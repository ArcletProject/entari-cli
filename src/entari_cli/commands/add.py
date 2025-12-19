from arclet.alconna import Alconna, Args, Arparma, CommandMeta, Option
from clilte import BasePlugin, CommandLine, PluginMetadata, register
from clilte.core import Next
from colorama import Fore

from entari_cli import i18n_
from entari_cli.config import EntariConfig
from entari_cli.project import get_project_root, install_dependencies
from entari_cli.py_info import check_package_installed, get_default_python, get_package_module


@register("entari_cli.plugins")
class AddPlugin(BasePlugin):
    def init(self):
        return Alconna(
            "add",
            Args["name/?", str],
            Option("--key", Args["key/", str], help_text=i18n_.commands.add.options.key()),
            Option("-D|--disabled", help_text=i18n_.commands.add.options.disabled()),
            Option("-O|--optional", help_text=i18n_.commands.add.options.optional()),
            Option("-p|--priority", Args["num/", int], help_text=i18n_.commands.add.options.priority()),
            meta=CommandMeta(i18n_.commands.add.description()),
        )

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="add",
            description=i18n_.commands.add.description(),
            version="0.1.0",
        )

    def dispatch(self, result: Arparma, next_: Next):
        from entari_cli.commands.setting import SelfSetting

        if result.find("add"):
            name = result.query[str]("add.name")
            if not name:
                name = input(f"{Fore.BLUE}{i18n_.commands.add.prompts.name}{Fore.RESET}").strip()
            cfg = EntariConfig.load(result.query[str]("cfg_path.path", None), get_project_root())
            name_ = name.replace("::", "arclet.entari.builtins.")
            if name_.startswith("arclet.entari.builtins."):
                key = name
                if not check_package_installed(name_, local=True):
                    return f"{Fore.RED}{i18n_.commands.add.prompts.builtins_not_found(name=f'{Fore.BLUE}{name_}')}{Fore.RESET}\n"  # noqa: E501
            else:
                if check_package_installed(name_, local=True):
                    key = result.query[str]("add.key.key", name_)
                elif check_package_installed(name_):
                    key = result.query[str]("add.key.key", get_package_module(name_) or name_.replace("-", "_"))
                elif not name_.count(".") and check_package_installed(f"entari_plugin_{name_}", local=True):
                    key = result.query[str]("add.key.key", name_)
                else:
                    retcode = install_dependencies(
                        CommandLine.current().get_plugin(SelfSetting),  # type: ignore
                        [name_],
                        get_default_python(get_project_root()),
                    )
                    if retcode != 0:
                        return f"{Fore.RED}{i18n_.commands.add.prompts.failed(name=f'{Fore.BLUE}{name_}', cmd=f'{Fore.GREEN}`entari new {name_}`')}{Fore.RESET}\n"  # noqa: E501
                    key = result.query[str]("add.key.key", get_package_module(name_) or name_.replace("-", "_"))
            cfg.plugin[key] = {}
            if result.find("add.disabled"):
                cfg.plugin[key]["$disable"] = True
            if result.find("add.optional"):
                cfg.plugin[key]["$optional"] = True
            if result.find("add.priority"):
                cfg.plugin[key]["priority"] = result.query[int]("add.priority.num", 16)
            cfg.save()
            return f"{Fore.GREEN}{i18n_.commands.add.prompts.success(name=name)}{Fore.RESET}\n"
        return next_(None)
