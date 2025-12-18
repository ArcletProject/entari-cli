from arclet.alconna import Alconna, Args, Arparma, CommandMeta, Option
from clilte import BasePlugin, CommandLine, PluginMetadata, register
from clilte.core import Next
from colorama import Fore

from entari_cli import i18n_
from entari_cli.config import EntariConfig
from entari_cli.project import get_project_root, uninstall_dependencies
from entari_cli.py_info import get_default_python


@register("entari_cli.plugins")
class RemovePlugin(BasePlugin):
    def init(self):
        return Alconna(
            "remove",
            Args["name/?", str],
            Option("--key", Args["key/", str], help_text=i18n_.commands.remove.options.key()),
            Option("-D|--keep", help_text=i18n_.commands.remove.options.keep()),
            meta=CommandMeta(i18n_.commands.remove.description()),
        )

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="remove",
            description=i18n_.commands.remove.description(),
            version="0.1.0",
        )

    def dispatch(self, result: Arparma, next_: Next):
        from entari_cli.commands.setting import SelfSetting

        if result.find("remove"):
            name = result.query[str]("remove.name")
            if not name:
                name = input(f"{Fore.BLUE}{i18n_.commands.remove.prompts.name()}{Fore.RESET}").strip()
            key = result.query[str]("remove.key.key", name)
            cfg = EntariConfig.load(result.query[str]("cfg_path.path", None), get_project_root())
            cfg.plugin.pop(key, None)
            cfg.save()
            if not result.find("remove.keep"):
                uninstall_dependencies(
                    CommandLine.current().get_plugin(SelfSetting),  # type: ignore
                    [name],
                    get_default_python(get_project_root()),
                )
            return f"{Fore.GREEN}{i18n_.commands.remove.prompts.success(name=name)}{Fore.RESET}\n"
        return next_(None)
