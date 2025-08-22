from arclet.alconna import Alconna, Args, Arparma, CommandMeta
from clilte import BasePlugin, PluginMetadata, register
from clilte.core import Next
from colorama import Fore

from entari_cli import i18n_
from entari_cli.config import EntariConfig


@register("entari_cli.plugins")
class RemovePlugin(BasePlugin):
    def init(self):
        return Alconna("remove", Args["name/?", str], meta=CommandMeta(i18n_.commands.remove.description()))

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="add",
            description=i18n_.commands.remove.description(),
            version="0.1.0",
        )

    def dispatch(self, result: Arparma, next_: Next):
        if result.find("remove"):
            name = result.query[str]("remove.name")
            if not name:
                name = input(f"{Fore.BLUE}{i18n_.commands.remove.prompts.name()}{Fore.RESET}").strip()
            cfg = EntariConfig.load(result.query[str]("cfg_path.path", None))
            cfg.plugin.pop(name, None)
            cfg.save()
            return f"{Fore.GREEN}{i18n_.commands.remove.prompts.success(name=name)}{Fore.RESET}\n"
        return next_(None)
