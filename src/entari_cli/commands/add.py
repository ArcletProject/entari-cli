from arclet.alconna import Alconna, Args, Arparma, CommandMeta, Option
from clilte import BasePlugin, PluginMetadata, register
from clilte.core import Next
from colorama import Fore

from entari_cli import i18n_
from entari_cli.config import EntariConfig
from entari_cli.py_info import check_package_installed


@register("entari_cli.plugins")
class AddPlugin(BasePlugin):
    def init(self):
        return Alconna(
            "add",
            Args["name/?", str],
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
        if result.find("add"):
            name = result.query[str]("add.name")
            if not name:
                name = input(f"{Fore.BLUE}{i18n_.commands.add.prompts.name}{Fore.RESET}").strip()
            cfg = EntariConfig.load(result.query[str]("cfg_path.path", None))
            name_ = name.replace("::", "arclet.entari.builtins.")
            if check_package_installed(name_):
                pass
            elif not name_.count(".") and check_package_installed(f"entari_plugin_{name_}"):
                pass
            else:
                return f"{Fore.RED}{i18n_.commands.add.prompts.failed(name=f'{Fore.BLUE}{name_}', cmd=f'{Fore.GREEN}`entari new {name_}`')}{Fore.RESET}\n"
            cfg.plugin[name] = {}
            if result.find("add.disabled"):
                cfg.plugin[name]["$disable"] = True
            if result.find("add.optional"):
                cfg.plugin[name]["$optional"] = True
            if result.find("add.priority"):
                cfg.plugin[name]["priority"] = result.query[int]("add.priority.num", 16)
            cfg.save()
            return f"{Fore.GREEN}{i18n_.commands.add.prompts.success(name=name)}{Fore.RESET}\n"
        return next_(None)
