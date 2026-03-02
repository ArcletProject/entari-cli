import json
import os
import re
import warnings
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from importlib import import_module
from io import StringIO
from pathlib import Path
from typing import Any, Callable, ClassVar, TypeVar, Union

from colorama import Fore
from ruamel.yaml import YAML
from tarina import safe_eval
from tomlkit import dumps, loads
from dotenv import dotenv_values

from entari_cli import i18n_
from entari_cli.utils import ask

EXPR_CONTEXT_PAT = re.compile(r"['\"]?\$\{\{\s?(?P<expr>[^}\s]+)\s?\}\}['\"]?")
T = TypeVar("T")


_loaders: dict[str, Callable[[str], dict]] = {}
_dumpers: dict[str, Callable[[dict, int, Union[str, None]], tuple[str, bool]]] = {}


class GetattrDict:
    def __init__(self, source: Mapping):
        self._source = source

    def __getitem__(self, item):
        return self._source[item]

    def __getattr__(self, item):
        try:
            return self._source[item]
        except KeyError as e:
            raise AttributeError(f"{item} not found") from e


def load_env_with_environment(
    *,
    base_files: tuple[str, ...] = (".env", ".env.local"),
    environment_key: str = "environment",
    encoding: str = "utf-8",
    use_lowercase_keys: bool = False,
) -> dict[str, str]:
    """
    1) 读取 .env / .env.local，拿到 environment
    2) 若 environment 有值，则再读取 .env.{environment}
    3) 最终用系统环境变量覆盖 dotenv 文件

    返回：合并后的 key -> value（value 可能为 None）
    """

    def norm(k: str) -> str:
        return k.lower() if use_lowercase_keys else k.upper()

    def read_one(path: str) -> dict[str, str]:
        p = Path(path).expanduser()
        if not p.is_file():
            return {}
        raw = dotenv_values(p, encoding=encoding)
        return {norm(k): v for k, v in raw.items() if v is not None}

    def read_many(paths: tuple[str, ...]) -> dict[str, str]:
        out: dict[str, str] = {}
        for fp in paths:
            out.update(read_one(fp))
        return out

    # 1) 先读基础文件（后读覆盖先读）
    dotenv_vars = read_many(base_files)

    # 用“当前已读到的 dotenv + 系统环境变量”来解析 environment（系统环境变量优先）
    sys_env: Mapping[str, str] = {norm(k): v for k, v in os.environ.items()}
    merged_for_env = {**dotenv_vars, **sys_env}
    environment = merged_for_env.get(norm(environment_key))

    # 2) 再读 .env.{environment}
    if environment:
        env_suffix = environment.strip()
        if env_suffix:
            dotenv_vars.update(read_one(f".env.{env_suffix}"))

    # 3) 最终合并：系统环境变量覆盖 dotenv
    final = {**dotenv_vars, **sys_env}
    return final


def check_env(file: Path):
    env = Path.cwd() / ".env"
    env_local = Path.cwd() / ".env.local"
    if env_local.exists():
        lines = env_local.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.startswith("ENTARI_CONFIG_FILE"):
                lines[i] = f"ENTARI_CONFIG_FILE='{file.resolve().as_posix()}'"
                with env_local.open("w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                break
    elif env.exists():
        lines = env.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.startswith("ENTARI_CONFIG_FILE"):
                lines[i] = f"ENTARI_CONFIG_FILE='{file.resolve().as_posix()}'"
                with env.open("w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                break
    else:
        with env_local.open("w+", encoding="utf-8") as f:
            f.write(f"\nENTARI_CONFIG_FILE='{file.resolve().as_posix()}'")


@dataclass
class EntariConfig:
    path: Path
    basic: dict[str, Any] = field(init=False)
    plugin: dict[str, dict] = field(init=False)
    prelude_plugin: list[str] = field(init=False)
    plugin_extra_files: list[str] = field(init=False)
    save_flag: bool = field(default=False)
    env_vars: dict[str, str] = field(default_factory=dict)
    _origin_data: dict[str, Any] = field(init=False)
    _env_replaced: dict[str, dict[int, tuple[str, int]]] = field(default_factory=dict, init=False)

    instance: ClassVar["EntariConfig"]

    def loader(self, path: Path):
        if not path.exists():
            return {}
        end = path.suffix.split(".")[-1]
        if end in _loaders:
            ctx = {"env": GetattrDict(os.environ)}

            with path.open("r", encoding="utf-8") as f:
                lines = f.readlines()
            for i, line in enumerate(lines):

                def handle(m: re.Match[str]):
                    expr = m.group("expr")
                    ans = safe_eval(expr, ctx)
                    self._env_replaced.setdefault(path.as_posix(), {})[i] = (line, len(ans.splitlines()))
                    return ans

                lines[i] = EXPR_CONTEXT_PAT.sub(handle, line)
            text = "".join(lines)
            return _loaders[end](text)

        raise ValueError(f"Unsupported file format: {path.suffix}")

    def dumper(self, path: Path, save_path: Path, data: dict, indent: int, apply_schema: bool):
        origin = self.loader(path) if path.exists() else data
        if "entari" in origin:
            origin["entari"] = data
        else:
            origin = data
        end = save_path.suffix.split(".")[-1]
        schema_file = None
        if apply_schema:
            schema_file = f"{save_path.stem}.schema.json"
        if end in _dumpers:
            ans, applied = _dumpers[end](origin, indent, schema_file)
            if self._env_replaced:
                lines = ans.splitlines(keepends=True)
                for i, (line, height) in self._env_replaced[path.as_posix()].items():
                    lines[i + applied] = line
                    for _ in range(height - 2):
                        lines.pop(i + applied + 1)
                ans = "".join(lines)
            with save_path.open("w", encoding="utf-8") as f:
                f.write(ans)
            return
        raise ValueError(f"Unsupported file format: {save_path.suffix}")

    def __post_init__(self):
        self.__class__.instance = self
        self.reload()

    @property
    def data(self) -> dict[str, Any]:
        return self._origin_data

    @property
    def prelude_plugin_names(self) -> list[str]:
        return [name for name in self.plugin_names if name in self.prelude_plugin]

    @property
    def plugin_names(self) -> list[str]:
        slots = [
            (name, self.plugin[name].get("$priority", 16))
            for name in self.plugin
            if not name.startswith("$") and not self.plugin[name].get("$optional", False)
        ]
        slots.sort(key=lambda x: x[1])
        return [name for name, _ in slots]

    def reload(self):
        if self.save_flag:
            self.save_flag = False
            return False
        data = self.loader(self.path)
        if "entari" in data:
            data = data["entari"]
        self.basic = data.setdefault("basic", {})
        self._origin_data = data
        self.plugin = data.setdefault("plugins", {})
        self.plugin_extra_files: list[str] = self.plugin.get("$files", [])  # type: ignore
        self.prelude_plugin = self.plugin.get("$prelude", [])  # type: ignore
        for key in list(self.plugin.keys()):
            if key.startswith("$"):
                continue
            value = self.plugin.pop(key)
            if key.startswith("~"):
                key = key[1:]
                if "$disable" not in value or isinstance(value["$disable"], bool):
                    value["$disable"] = True
            elif key.startswith("?"):
                key = key[1:]
                value["$optional"] = True
            self.plugin[key] = value
        for file in self.plugin_extra_files:
            path = Path(file)
            if not path.exists():
                raise FileNotFoundError(file)
            if path.is_dir():
                for _path in path.iterdir():
                    if not _path.is_file() or _path.name.endswith(".schema.json"):
                        continue
                    self.plugin[_path.stem] = self.loader(_path)
            elif path.name.endswith(".schema.json"):
                self.plugin[path.stem] = self.loader(path)
        return True

    def dump(self, indent: int = 2, apply_schema: bool = False):
        basic = self._origin_data.setdefault("basic", {})
        if "log" not in basic and ("log_level" in basic or "log_ignores" in basic):
            basic["log"] = {}
            if "log_level" in basic:
                basic["log"]["level"] = basic.pop("log_level")
            if "log_ignores" in basic:
                basic["log"]["ignores"] = basic.pop("log_ignores")

        def _clean(value: dict):
            return {k: v for k, v in value.items() if k not in {"$path", "$static"}}

        if self.plugin_extra_files:
            for file in self.plugin_extra_files:
                path = Path(file)
                if path.is_file() and not path.name.endswith(".schema.json"):
                    self.dumper(path, path, _clean(self.plugin.pop(path.stem)), indent, apply_schema)
                else:
                    for _path in path.iterdir():
                        if _path.is_file() and not _path.name.endswith(".schema.json"):
                            self.dumper(_path, _path, _clean(self.plugin.pop(_path.stem)), indent, apply_schema)
        for key in list(self.plugin.keys()):
            if key.startswith("$"):
                continue
            value = self.plugin.pop(key)
            if "$disable" in value and isinstance(value["$disable"], bool):
                key = f"~{key}" if value["$disable"] else key
                value.pop("$disable", None)
            if "$optional" in value:
                key = f"?{key}" if value["$optional"] else key
                value.pop("$optional", None)
            self.plugin[key] = _clean(value)
        return self._origin_data

    def save(self, path: Union[str, os.PathLike[str], None] = None, indent: int = 2, apply_schema: bool = False):
        self.save_flag = True
        self.dumper(self.path, Path(path or self.path), self.dump(indent, apply_schema), indent, apply_schema)

    @classmethod
    def load(cls, path: Union[str, os.PathLike[str], None] = None, cwd: Union[Path, None] = None) -> "EntariConfig":
        env_vars = load_env_with_environment()
        cwd = cwd or Path.cwd()
        if not path:
            if "ENTARI_CONFIG_FILE" in env_vars:
                _path = Path(env_vars["ENTARI_CONFIG_FILE"])
            elif (cwd / ".entari.json").exists():
                _path = cwd / ".entari.json"
            elif (cwd / "entari.toml").exists():
                _path = cwd / ".entari.toml"
            elif (cwd / ".entari.toml").exists():
                _path = cwd / ".entari.toml"
            elif (cwd / "entari.yaml").exists():
                _path = cwd / "entari.yaml"
            else:
                _path = cwd / "entari.yml"
        else:
            _path = Path(path)
        if "ENTARI_CONFIG_EXTENSION" in env_vars:
            ext_mods = env_vars["ENTARI_CONFIG_EXTENSION"].split(";")
            for ext_mod in ext_mods:
                if not ext_mod:
                    continue
                ext_mod = ext_mod.replace("::", "arclet.entari.config.format.")
                try:
                    import_module(ext_mod)
                except ImportError as e:
                    warnings.warn(i18n_.config.ext_failed(ext_mod=ext_mod, error=repr(e)), ImportWarning)
        if not _path.exists():
            return cls(_path, env_vars=env_vars)
        if not _path.is_file():
            raise ValueError(f"{_path} is not a file")
        return cls(_path, env_vars=env_vars)


def register_loader(*ext: str):
    """Register a loader for a specific file extension."""

    def decorator(func: Callable[[str], dict]):
        for e in ext:
            _loaders[e] = func
        return func

    return decorator


def register_dumper(*ext: str):
    """Register a dumper for a specific file extension."""

    def decorator(func: Callable[[dict, int, Union[str, None]], tuple[str, bool]]):
        for e in ext:
            _dumpers[e] = func
        return func

    return decorator


@register_loader("json")
def json_loader(text: str) -> dict:
    return json.loads(text)


@register_dumper("json")
def json_dumper(origin: dict, indent: int, schema_file: Union[str, None] = None):
    schema_applied = False
    if schema_file and "$schema" not in origin:
        origin = {"$schema": f"{schema_file}", **origin}
        schema_applied = True
    return json.dumps(origin, indent=indent, ensure_ascii=False), schema_applied


@register_loader("yaml", "yml")
def yaml_loader(text: str) -> dict:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml.load(StringIO(text))


@register_dumper("yaml", "yml")
def yaml_dumper(origin: dict, indent: int, schema_file: Union[str, None] = None):
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=indent, sequence=indent + 2, offset=indent)
    yaml.width = 4096
    sio = StringIO()
    yaml.dump(origin, sio)
    ans = sio.getvalue()
    schema_applied = False
    if schema_file:
        root = Path.cwd()
        if (root / ".vscode").exists():
            if not ans.startswith("# yaml-language-server: $schema="):
                ans = f"# yaml-language-server: $schema={schema_file}\n{ans}"
                schema_applied = True
        elif not ans.startswith("# $schema:"):
            ans = f"# $schema: {schema_file}\n{ans}"
            schema_applied = True
    return ans, schema_applied


@register_loader("toml")
def toml_loader(text: str) -> dict[str, Any]:
    """
    Load a TOML file and return its content as a dictionary.
    """
    if loads is None:
        raise RuntimeError("tomlkit is not installed. Please install with `arclet-entari[toml]`")
    return loads(text)


@register_dumper("toml")
def toml_dumper(origin: dict[str, Any], indent: int = 4, schema_file: Union[str, None] = None) -> tuple[str, bool]:
    """
    Dump a dictionary to a TOML file.
    """
    if dumps is None:
        raise RuntimeError("tomlkit is not installed. Please install with `arclet-entari[toml]`")
    ans = dumps(origin)
    schema_applied = False
    if schema_file and not ans.startswith("# schema: "):
        ans = f"# schema: {schema_file}\n{ans}"
        schema_applied = True
    return ans, schema_applied


@contextmanager
def create_config(cfg_path: Union[str, None], is_dev: bool = False, format_: Union[str, None] = None):
    if cfg_path:
        _path = Path(cfg_path)
    else:
        if format_ is None:
            format_ = ask(i18n_.config.ask_format(), "yml").strip().lower()
        if format_ not in {"yaml", "yml", "json", "toml"}:
            return f"{Fore.RED}{i18n_.config.not_supported(suffix=format_)}{Fore.RESET}"
        _path = Path.cwd() / f"{'.entari' if format_ in {'json', 'toml'} else 'entari'}.{format_}"
    obj = EntariConfig.load(_path)
    if _path.exists():
        print(i18n_.config.exists(path=_path))
    else:
        obj.basic |= {
            "network": [{"type": "websocket", "host": "localhost", "port": 5140, "path": ""}],
            "ignore_self_message": True,
            "log": {"level": "info"},
            "prefix": ["/"],
            "schema": True,
        }
        if is_dev:
            obj.plugin |= {  # type: ignore
                "$prelude": ["::auto_reload"],
                ".record_message": {
                    "record_send": True,
                },
                "::echo": {},
                "::help": {},
                "::inspect": {},
                "::auto_reload": {"watch_config": True},
            }
        else:
            obj.plugin |= {".record_message": {}, "::echo": {}, "::help": {}, "::inspect": {}}
        print(i18n_.config.created(path=_path))
    yield obj
    obj.save()
    check_env(_path)
