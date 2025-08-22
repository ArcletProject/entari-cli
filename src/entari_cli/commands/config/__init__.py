from pathlib import Path

from arclet.alconna import Alconna, Arparma, CommandMeta, Option, Subcommand
from clilte import BasePlugin, PluginMetadata, register
from clilte.core import Next
from colorama import Fore

from entari_cli import i18n_
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
                Option("-d|--dev", help_text=i18n_.commands.config.options.dev()),
                help_text=i18n_.commands.config.options.new(),
            ),
            Subcommand("current", help_text=i18n_.commands.config.options.current()),
            meta=CommandMeta(i18n_.commands.config.description()),
        )

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="config",
            description=i18n_.commands.config.description(),
            version="0.1.0",
        )

    def dispatch(self, result: Arparma, next_: Next):
        if result.find("config.new"):
            is_dev = result.find("config.new.dev")
            names = result.query[tuple[str, ...]]("config.new.plugins.names", ())
            if (path := result.query[str]("cfg_path.path", None)) is None:
                _path = Path.cwd() / "entari.yml"
            else:
                _path = Path(path)
            if _path.exists():
                return i18n_.commands.config.messages.exist(path=_path)
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
                return i18n_.commands.config.messages.created(path=_path)
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
                return i18n_.commands.config.messages.created(path=_path)
            return i18n_.commands.config.messages.not_supported(suffix=_path.suffix)
        if result.find("config.current"):
            cfg = EntariConfig.load()
            return i18n_.commands.config.messages.current(path=f"{Fore.BLUE}{cfg.path.resolve()!s}{Fore.RESET}")
        if result.find("config"):
            return self.command.get_help()
        return next_(None)
