from pathlib import Path

from arclet.alconna import Alconna, Arparma, CommandMeta, Option, Subcommand
from clilte import BasePlugin, PluginMetadata, register
from clilte.core import Next
from colorama import Fore

from entari_cli.config import EntariConfig
from entari_cli.template import (
    JSON_BASIC_TEMPLATE,
    JSON_PLUGIN_BLANK_TEMPLATE,
    JSON_PLUGIN_COMMON_TEMPLATE,
    JSON_PLUGIN_DEV_TEMPLATE,
    YAML_BASIC_TEMPLATE,
    YAML_PLUGIN_BLANK_TEMPLATE,
    YAML_PLUGIN_COMMON_TEMPLATE,
    YAML_PLUGIN_DEV_TEMPLATE,
)


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


@register("entari_cli.plugins")
class ConfigPlugin(BasePlugin):
    def init(self):
        return Alconna(
            "config",
            Subcommand(
                "new",
                Option("-d|--dev", help_text="是否生成开发用配置文件"),
                help_text="新建一个 Entari 配置文件",
            ),
            Subcommand("current", help_text="查看当前配置文件"),
            meta=CommandMeta("配置文件操作"),
        )

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="config",
            description="配置文件操作",
            version="0.1.0",
        )

    def dispatch(self, result: Arparma, next_: Next):
        if result.find("config.new"):
            is_dev = result.find("config.new.dev")
            names = result.query[tuple[str, ...]]("config.new.plugins.names", ())
            if (path := result.query[str]("cfg_path.path", None)) is None:
                _path = Path.cwd() / ".entari.json"
                if (Path.cwd() / "entari.yml").exists():
                    _path = Path.cwd() / "entari.yml"
            else:
                _path = Path(path)
            if _path.exists():
                print(f"{_path} already exists")
                return
            if _path.suffix.startswith(".json"):
                if names:
                    PT = JSON_PLUGIN_BLANK_TEMPLATE.format(plugins=",\n".join(f'    "{name}": {{}}' for name in names))
                elif is_dev:
                    PT = JSON_PLUGIN_DEV_TEMPLATE
                else:
                    PT = JSON_PLUGIN_COMMON_TEMPLATE

                with _path.open("w", encoding="utf-8") as f:
                    f.write(JSON_BASIC_TEMPLATE + PT)
                check_env(_path)
                print(f"Config file created at {_path}")
                return
            if _path.suffix in (".yaml", ".yml"):
                if names:
                    PT = YAML_PLUGIN_BLANK_TEMPLATE.format(plugins="\n".join(f"  {name}: {{}}" for name in names))
                elif is_dev:
                    PT = YAML_PLUGIN_DEV_TEMPLATE
                else:
                    PT = YAML_PLUGIN_COMMON_TEMPLATE

                with _path.open("w", encoding="utf-8") as f:
                    f.write(YAML_BASIC_TEMPLATE + PT)
                check_env(_path)
                print(f"Config file created at {_path}")
                return
            print(f"Unsupported file extension: {_path.suffix}")
            return
        if result.find("config.current"):
            cfg = EntariConfig.load()
            return f"Current config file:\n{Fore.BLUE}{cfg.path.resolve()!s}"
        if result.find("config"):
            return self.command.get_help()
        return next_(None)
