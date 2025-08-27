from arclet.alconna import Args, Arparma, Option
from clilte import BasePlugin, PluginMetadata, register
from clilte.core import Next

from entari_cli import i18n_


@register("entari_cli.plugins")
class ConfigPath(BasePlugin):
    def init(self):
        return Option("-c|--config", Args["path/", str], help_text=i18n_.commands.config_path(), dest="cfg_path"), True

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="cfg_path",
            description=i18n_.commands.config_path(),
            version="0.1.0",
        )

    def dispatch(self, result: Arparma, next_: Next):
        return next_(None)
