from arclet.alconna import Alconna, Args, Arparma, CommandMeta, Option
from clilte import BasePlugin, CommandLine, PluginMetadata, register
from clilte.core import Next
from colorama import Fore

from entari_cli import i18n_
from entari_cli.config import EntariConfig
from entari_cli.project import get_project_root, uninstall_dependencies
from entari_cli.py_info import check_package_installed, get_default_python, get_module_package, get_package_module


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
            name_ = name.replace("::", "arclet.entari.builtins.")
            if name_.startswith("arclet.entari.builtins."):
                key = name
                if not check_package_installed(name_, local=True):
                    return f"{Fore.RED}{i18n_.commands.remove.prompts.builtins_not_found(name=f'{Fore.BLUE}{name_}')}{Fore.RESET}\n"  # noqa: E501
            else:
                if check_package_installed(name_, local=True):
                    key = result.query[str]("remove.key.key", name_)
                    name = get_module_package(name_)
                elif check_package_installed(name_):
                    name = name_
                    key = result.query[str]("remove.key.key", get_package_module(name_) or name_.replace("-", "_"))
                elif not name_.count(".") and check_package_installed(f"entari_plugin_{name_}", local=True):
                    name = f"entari-plugin-{name_}"
                    key = result.query[str]("remove.key.key", name_)
                else:
                    key = result.query[str]("remove.key.key", name)
                    name = None
            cfg = EntariConfig.load(result.query[str]("cfg_path.path", None), get_project_root())
            if key not in cfg.plugin:
                return f"{Fore.RED}{i18n_.commands.remove.prompts.not_found(name=f'{Fore.BLUE}{name_}{Fore.RED}')}{Fore.RESET}\n"  # noqa: E501
            cfg.plugin.pop(key, None)
            cfg.save()
            if not result.find("remove.keep") and not name_.count(".") and name:
                uninstall_dependencies(
                    CommandLine.current().get_plugin(SelfSetting),  # type: ignore
                    [name],
                    get_default_python(get_project_root()),
                )
            return f"{Fore.GREEN}{i18n_.commands.remove.prompts.success(name=name_)}{Fore.RESET}\n"
        return next_(None)
