from importlib.util import find_spec

from arclet.alconna import Alconna, Args, Arparma, CommandMeta, Option
from clilte import BasePlugin, PluginMetadata, register
from clilte.core import Next
from colorama import Fore

from entari_cli.config import EntariConfig


@register("entari_cli.plugins")
class AddPlugin(BasePlugin):
    def init(self):
        return Alconna(
            "add",
            Args["name/?", str],
            Option("-D|--disabled", help_text="是否插件初始禁用"),
            Option("-O|--optional", help_text="是否仅存储插件配置而不加载插件"),
            Option("-p|--priority", Args["num/", int], help_text="插件加载优先级"),
            meta=CommandMeta("添加一个 Entari 插件到配置文件中"),
        )

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="add",
            description="添加一个 Entari 插件到配置文件中",
            version="0.1.0",
        )

    def dispatch(self, result: Arparma, next_: Next):
        if result.find("add"):
            name = result.query[str]("add.name")
            if not name:
                print(f"{Fore.BLUE}Please specify a plugin name:")
                name = input(f"{Fore.RESET}>>> ").strip()
            cfg = EntariConfig.load(result.query[str]("cfg_path.path", None))
            name_ = name.replace("::", "arclet.entari.builtins.")
            if find_spec(name_):
                pass
            elif not name_.count(".") and find_spec(f"entari_plugin_{name_}"):
                pass
            else:
                return f"{Fore.BLUE}{name_!r}{Fore.RED} not found.\nYou should installed it, or run {Fore.GREEN}`entari new {name_}`{Fore.RESET}"
            cfg.plugin[name] = {}
            if result.find("add.disabled"):
                cfg.plugin[name]["$disable"] = True
            if result.find("add.optional"):
                cfg.plugin[name]["$optional"] = True
            if result.find("add.priority"):
                cfg.plugin[name]["priority"] = result.query[int]("add.priority.num", 16)
            cfg.save()
            return f"{Fore.GREEN}Plugin {name!r} added to configuration file successfully.{Fore.RESET}\n"
        return next_(None)
