from pathlib import Path
import sys

from arclet.alconna import Alconna, Args, Arparma, CommandMeta, MultiVar, Option
from clilte import BasePlugin, PluginMetadata, register
from clilte.core import Next
from colorama import Fore

from entari_cli import i18n_
from entari_cli.process import call_pip
from entari_cli.project import ensure_python
from entari_cli.py_info import check_package_installed
from entari_cli.utils import ask
from entari_cli.venv import get_venv_like_prefix


@register("entari_cli.plugins")
class InitEnv(BasePlugin):
    def init(self):
        return Alconna(
            "init",
            Option("-py|--python", Args["path/", str], help_text=i18n_.commands.init.options.python()),
            Option("--pip-args", Args["params/", MultiVar(str)], help_text=i18n_.commands.init.options.pip_args()),
            meta=CommandMeta(i18n_.commands.init.description()),
        )

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="init",
            description=i18n_.commands.init.description(),
            version="0.1.0",
        )

    def dispatch(self, result: Arparma, next_: Next):
        if result.find("init"):
            python = result.query[str]("new.python.path", "")
            args = result.query[tuple[str, ...]]("new.pip_args.params", ())

            python_path = sys.executable
            if get_venv_like_prefix(sys.executable)[0] is None:
                ans = ask(i18n_.venv.ask_create(), "Y/n").strip().lower()
                use_venv = ans in {"yes", "true", "t", "1", "y", "yea", "yeah", "yep", "sure", "ok", "okay", "", "y/n"}
                if use_venv:
                    python_path = str(ensure_python(Path.cwd(), python).executable)
            if check_package_installed("arclet.entari", python_path):
                return f"{Fore.YELLOW}{i18n_.commands.init.messages.initialized()}{Fore.RESET}"
            else:
                ret_code = call_pip(sys.executable, "install", "arclet-entari[full]", *args)
                if ret_code != 0:
                    return f"{Fore.RED}{i18n_.project.install_failed()}{Fore.RESET}"
            return f"{Fore.GREEN}{i18n_.commands.init.messages.success()}{Fore.RESET}"
        return next_(None)
