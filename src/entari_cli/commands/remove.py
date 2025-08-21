from arclet.alconna import Alconna, Args, Arparma, CommandMeta
from clilte import BasePlugin, PluginMetadata, register
from clilte.core import Next
from colorama import Fore

from entari_cli.config import EntariConfig


@register("entari_cli.plugins")
class RemovePlugin(BasePlugin):
    def init(self):
        return Alconna("remove", Args["name/?", str], meta=CommandMeta("从配置文件中移除一个 Entari 插件"))

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="add",
            description="从配置文件中移除一个 Entari 插件",
            version="0.1.0",
        )

    def dispatch(self, result: Arparma, next_: Next):
        if result.find("remove"):
            name = result.query[str]("remove.name")
            if not name:
                print(f"{Fore.BLUE}Please specify a plugin name:")
                name = input(f"{Fore.RESET}>>> ").strip()
            cfg = EntariConfig.load(result.query[str]("cfg_path.path", None))
            cfg.plugin.pop(name, None)
            cfg.save()
            return f"{Fore.GREEN}Plugin {name!r} removed from configuration file successfully.{Fore.RESET}\n"
        return next_(None)
