from arclet.alconna import Args, Arparma, Option
from clilte import BasePlugin, PluginMetadata, register
from clilte.core import Next


@register("entari_cli.plugins")
class ConfigPath(BasePlugin):
    def init(self):
        return Option("-c|--config", Args["path/", str], help_text="指定配置文件路径", dest="cfg_path"), True

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="cfg_path",
            description="指定配置文件路径",
            version="0.1.0",
        )

    def dispatch(self, result: Arparma, next_: Next):
        return next_(None)
