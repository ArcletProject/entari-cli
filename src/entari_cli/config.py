from contextlib import contextmanager
from dataclasses import dataclass, field
from importlib import import_module
from io import StringIO
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, ClassVar, TypeVar, Union
import warnings

from colorama import Fore
from ruamel.yaml import YAML
from tomlkit import dumps, loads

from entari_cli import i18n_
from entari_cli.utils import ask

ENV_CONTEXT_PAT = re.compile(r"['\"]?\$\{\{\s?env\.(?P<name>[^}\s]+)\s?\}\}['\"]?")
T = TypeVar("T")


_loaders: dict[str, Callable[[str], dict]] = {}
_dumpers: dict[str, Callable[[Path, dict, int], None]] = {}


def check_env(file: Path):
    env = Path.cwd() / ".env"
    if env.exists():
        lines = env.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.startswith("ENTARI_CONFIG_FILE"):
                lines[i] = f"ENTARI_CONFIG_FILE='{file.resolve().as_posix()}'"
                with env.open("w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                break
    else:
        with env.open("w+", encoding="utf-8") as f:
            f.write(f"\nENTARI_CONFIG_FILE='{file.resolve().as_posix()}'")


@dataclass
class EntariConfig:
    path: Path
    basic: dict[str, Any] = field(init=False)
    plugin: dict[str, dict] = field(init=False)
    prelude_plugin: list[str] = field(init=False)
    plugin_extra_files: list[str] = field(init=False)
    save_flag: bool = field(default=False)
    _origin_data: dict[str, Any] = field(init=False)

    instance: ClassVar["EntariConfig"]

    @classmethod
    def loader(cls, path: Path):
        if not path.exists():
            return {}
        end = path.suffix.split(".")[-1]
        if end in _loaders:
            with path.open("r", encoding="utf-8") as f:
                text = f.read()
                text = ENV_CONTEXT_PAT.sub(lambda m: os.environ.get(m["name"], ""), text)
                return _loaders[end](text)

        raise ValueError(f"Unsupported file format: {path.suffix}")

    @classmethod
    def dumper(cls, path: Path, save_path: Path, data: dict, indent: int):
        origin = cls.loader(path) if path.exists() else data
        if "entari" in origin:
            origin["entari"] = data
        end = save_path.suffix.split(".")[-1]
        if end in _dumpers:
            _dumpers[end](save_path, origin, indent)
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
                    if not _path.is_file():
                        continue
                    self.plugin[_path.stem] = self.loader(_path)
            else:
                self.plugin[path.stem] = self.loader(path)
        return True

    def dump(self, indent: int = 2):
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
                if path.is_file():
                    self.dumper(path, path, _clean(self.plugin.pop(path.stem)), indent)
                else:
                    for _path in path.iterdir():
                        if _path.is_file():
                            self.dumper(_path, _path, _clean(self.plugin.pop(_path.stem)), indent)
        for key in list(self.plugin.keys()):
            if key.startswith("$"):
                continue
            value = self.plugin.pop(key)
            if "$disable" in value:
                key = f"~{key}" if value["$disable"] else key
                value.pop("$disable", None)
            if "$optional" in value:
                key = f"?{key}" if value["$optional"] else key
                value.pop("$optional", None)
            self.plugin[key] = _clean(value)
        return self._origin_data

    def save(self, path: Union[str, os.PathLike[str], None] = None, indent: int = 2):
        self.save_flag = True
        self.dumper(self.path, Path(path or self.path), self.dump(indent), indent)

    @classmethod
    def load(cls, path: Union[str, os.PathLike[str], None] = None, cwd: Union[Path, None] = None) -> "EntariConfig":
        try:
            import dotenv

            dotenv.load_dotenv()
        except ImportError:
            dotenv = None  # noqa
            pass
        cwd = cwd or Path.cwd()
        if not path:
            if "ENTARI_CONFIG_FILE" in os.environ:
                _path = Path(os.environ["ENTARI_CONFIG_FILE"])
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
        if "ENTARI_CONFIG_EXTENSION" in os.environ:
            ext_mods = os.environ["ENTARI_CONFIG_EXTENSION"].split(";")
            for ext_mod in ext_mods:
                if not ext_mod:
                    continue
                ext_mod = ext_mod.replace("::", "arclet.entari.config.format.")
                try:
                    import_module(ext_mod)
                except ImportError as e:
                    warnings.warn(i18n_.config.ext_failed(ext_mod=ext_mod, error=repr(e)), ImportWarning)
        if not _path.exists():
            return cls(_path)
        if not _path.is_file():
            raise ValueError(f"{_path} is not a file")
        return cls(_path)


def register_loader(*ext: str):
    """Register a loader for a specific file extension."""

    def decorator(func: Callable[[str], dict]):
        for e in ext:
            _loaders[e] = func
        return func

    return decorator


def register_dumper(*ext: str):
    """Register a dumper for a specific file extension."""

    def decorator(func: Callable[[Path, dict, int], None]):
        for e in ext:
            _dumpers[e] = func
        return func

    return decorator


@register_loader("json")
def json_loader(text: str) -> dict:
    return json.loads(text)


@register_dumper("json")
def json_dumper(save_path: Path, origin: dict, indent: int):
    with save_path.open("w+", encoding="utf-8") as f:
        json.dump(origin, f, indent=indent, ensure_ascii=False)


@register_loader("yaml", "yml")
def yaml_loader(text: str) -> dict:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml.load(StringIO(text))


@register_dumper("yaml", "yml")
def yaml_dumper(save_path: Path, origin: dict, indent: int):
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=indent, sequence=indent + 2, offset=indent)
    with save_path.open("w+", encoding="utf-8") as f:
        yaml.dump(origin, f)


@register_loader("toml")
def toml_loader(text: str) -> dict[str, Any]:
    """
    Load a TOML file and return its content as a dictionary.
    """
    if loads is None:
        raise RuntimeError("tomlkit is not installed. Please install with `arclet-entari[toml]`")
    return loads(text)


@register_dumper("toml")
def toml_dumper(save_path: Path, origin: dict[str, Any], indent: int = 4):
    """
    Dump a dictionary to a TOML file.
    """
    if dumps is None:
        raise RuntimeError("tomlkit is not installed. Please install with `arclet-entari[toml]`")
    with open(save_path, "w+", encoding="utf-8") as f:
        f.write(dumps(origin))


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
            "network": [{"type": "websocket", "host": "127.0.0.1", "port": 5140, "path": "satori"}],
            "ignore_self_message": True,
            "log": {"level": "info"},
            "prefix": ["/"],
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
