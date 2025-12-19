from arclet.alconna import Alconna, Arparma, CommandMeta, Option
from clilte import BasePlugin, CommandLine, PluginMetadata, register
from clilte.core import Next
from colorama import Fore

from entari_cli import i18n_
from entari_cli.config import EntariConfig
from entari_cli.consts import YES
from entari_cli.project import get_project_root, install_dependencies, uninstall_dependencies
from entari_cli.py_info import check_package_installed, get_default_python
from entari_cli.utils import ask

ADAPTERS = {
    "OneBot11 Forward": ["@onebot11.forward", "satori-python-adapter-onebot11", "OneBot11 正向 WS 协议适配器"],
    "OneBot11 Reverse": ["@onebot11.reverse", "satori-python-adapter-onebot11", "OneBot11 反向 WS 协议适配器"],
    "Console": ["@console", "satori-python-adapter-console", "控制台适配器"],
    "Satori": ["@satori", "satori-python-adapter-satori", "Satori 协议适配器"],
    "Milky": ["@milky.main", "satori-python-adapter-milky", "Milky 协议适配器"],
    "Milky Webhook": ["@milky.webhook", "satori-python-adapter-milky", "Milky Webhook 协议适配器"],
    "Nekobot": ["nekobot.main", "nekobot", "Lagrange 适配器"],
}


@register("entari_cli.plugins")
class AdapterPlugin(BasePlugin):
    def init(self):
        return Alconna(
            "adapter",
            Option("add", help_text=i18n_.commands.adapter.options.add()),
            Option("list", help_text=i18n_.commands.adapter.options.list()),
            Option("remove", help_text=i18n_.commands.adapter.options.remove()),
            meta=CommandMeta(i18n_.commands.adapter.description()),
        )

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="remove",
            description=i18n_.commands.adapter.description(),
            version="0.1.0",
        )

    def dispatch(self, result: Arparma, next_: Next):
        from entari_cli.commands.setting import SelfSetting

        if result.find("adapter.list"):
            output = f"{Fore.GREEN}{i18n_.commands.adapter.messages.list_header()}{Fore.RESET}\n"
            cfg = EntariConfig.load(result.query[str]("cfg_path.path", None), get_project_root())
            adapters = {adapter["$path"].replace("satori.adapters.", "@") for adapter in cfg.data.get("adapters", [])}
            offset = max(len(name) for name in ADAPTERS.keys()) + 1
            for name, (key, _, desc) in ADAPTERS.items():
                status = key in adapters
                output += f"  {Fore.BLUE}{name:<{offset}}{Fore.RESET}  {desc}" + (" (已安装)" if status else "") + "\n"
            return output

        if result.find("adapter.add"):
            cfg = EntariConfig.load(result.query[str]("cfg_path.path", None), get_project_root())
            if "server" not in cfg.plugin and "entari_plugin_server" not in cfg.plugin:
                print(f"{Fore.YELLOW}{i18n_.commands.adapter.messages.server_not_installed()}{Fore.RESET}\n")
                ans = (
                    ask(f"{Fore.BLUE}{i18n_.commands.adapter.prompts.confirm_install()}{Fore.RESET} " "Y/n")
                    .strip()
                    .lower()
                )
                continue_install = ans in YES
                if not continue_install:
                    return next_(None)
            adapters = {adapter["$path"].replace("satori.adapters.", "@") for adapter in cfg.data.get("adapters", [])}
            install = []
            for name, (key, pkg, desc) in ADAPTERS.items():
                if key not in adapters:
                    install.append((name, key, pkg, desc))
            if not install:
                return f"{Fore.YELLOW}{i18n_.commands.adapter.messages.all_installed()}{Fore.RESET}\n"
            offset = max(len(slot[0]) for slot in install) + 1
            print(i18n_.commands.adapter.prompts.select_adapter())
            for i, (name, _, pkg, desc) in enumerate(install):
                print(f"{i:>2}. {Fore.GREEN}{name:<{offset}}{Fore.RESET} {desc} ({pkg})")
            selection = ask(i18n_.commands.adapter.prompts.please_select())
            if not selection.isdigit() or int(selection) < 0 or int(selection) >= len(install):
                raise ValueError(i18n_.commands.adapter.prompts.invalid_selection())
            name, key, pkg, _ = install[int(selection)]
            if not check_package_installed(pkg):
                retcode = install_dependencies(
                    CommandLine.current().get_plugin(SelfSetting),  # type: ignore
                    [pkg],
                    get_default_python(get_project_root()),
                )
                if retcode != 0:
                    return f"{Fore.RED}{i18n_.commands.adapter.messages.install_failed(name=f'{Fore.BLUE}{pkg}')}{Fore.RESET}\n"  # noqa: E501
            cfg.data.setdefault("adapters", [])
            cfg.data["adapters"].append({"$path": key})
            cfg.save()
            return f"{Fore.GREEN}{i18n_.commands.adapter.messages.add_success(name=name)}{Fore.RESET}\n"

        if result.find("adapter.remove"):
            cfg = EntariConfig.load(result.query[str]("cfg_path.path", None), get_project_root())
            adapters = {adapter["$path"].replace("satori.adapters.", "@") for adapter in cfg.data.get("adapters", [])}
            install = []
            for name, (key, pkg, desc) in ADAPTERS.items():
                if key in adapters:
                    install.append((name, key, pkg, desc))
            if not install:
                return f"{Fore.YELLOW}{i18n_.commands.adapter.messages.none_installed()}{Fore.RESET}\n"
            offset = max(len(slot[0]) for slot in install) + 1
            print(i18n_.commands.adapter.prompts.select_adapter())
            for i, (name, _, pkg, desc) in enumerate(install):
                print(f"{i:>2}. {Fore.GREEN}{name:<{offset}}{Fore.RESET} {desc} ({pkg})")
            selection = ask(i18n_.commands.adapter.prompts.please_select())
            if not selection.isdigit() or int(selection) < 0 or int(selection) >= len(install):
                raise ValueError(i18n_.commands.adapter.prompts.invalid_selection())
            name, key, pkg, _ = install[int(selection)]
            cfg.data["adapters"] = [
                adapter
                for adapter in cfg.data.get("adapters", [])
                if adapter["$path"].replace("satori.adapters.", "@") != key
            ]
            cfg.save()
            if check_package_installed(pkg):
                uninstall_dependencies(
                    CommandLine.current().get_plugin(SelfSetting),  # type: ignore
                    [name],
                    get_default_python(get_project_root()),
                )
            return f"{Fore.GREEN}{i18n_.commands.adapter.messages.remove_success(name=name)}{Fore.RESET}\n"
        return next_(None)
