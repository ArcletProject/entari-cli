import sys

from arclet.alconna import Alconna, Args, Arparma, CommandMeta, MultiVar, Option
from clilte import BasePlugin, CommandLine, PluginMetadata, register
from clilte.core import Next
from colorama import Fore
import tomlkit

from entari_cli import i18n_
from entari_cli.config import create_config
from entari_cli.consts import ENTARI_VERSION
from entari_cli.project import ensure_python, get_project_root, install_dependencies
from entari_cli.py_info import PythonInfo, check_package_installed, get_package_version
from entari_cli.setting import set_item
from entari_cli.template import WORKSPACE_PROJECT_TEMPLATE
from entari_cli.utils import ask
from entari_cli.venv import get_in_project_venv, get_venv_like_prefix


@register("entari_cli.plugins")
class InitEnv(BasePlugin):
    def init(self):
        return Alconna(
            "init",
            Option("-d|--dev", help_text=i18n_.commands.init.options.develop()),
            Option("-py|--python", Args["path/", str], help_text=i18n_.commands.init.options.python()),
            Option(
                "--install-args",
                Args["params/", MultiVar(str)],
                help_text=i18n_.commands.init.options.install_args(),
                dest="install",
            ),
            meta=CommandMeta(i18n_.commands.init.description()),
        )

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="init",
            description=i18n_.commands.init.description(),
            version="0.1.0",
        )

    def dispatch(self, result: Arparma, next_: Next):
        from entari_cli.commands.setting import SelfSetting

        if result.find("init"):
            cwd = get_project_root()
            python = result.query[str]("init.python.path", "")
            args = result.query[tuple[str, ...]]("init.install.params", ())
            is_dev = result.find("init.dev")
            extra = ["yaml", "cron", "dotenv"]
            if is_dev:
                extra += ["reload"]
            extras = ",".join(extra)
            python_path = sys.executable
            if get_venv_like_prefix(sys.executable)[0] is None or get_in_project_venv(cwd) is None:
                ans = ask(i18n_.venv.ask_create(), "Y/n").strip().lower()
                use_venv = ans in {"yes", "true", "t", "1", "y", "yea", "yeah", "yep", "sure", "ok", "okay", "", "y/n"}
                if use_venv:
                    python_path = str(ensure_python(cwd, python).executable)
                print(f"{Fore.GREEN}{i18n_.commands.init.messages.success()}{Fore.RESET}")
            toml_file = cwd / "pyproject.toml"
            if not toml_file.exists():
                info = PythonInfo.from_path(python_path)
                with toml_file.open("w", encoding="utf-8") as f:
                    f.write(
                        WORKSPACE_PROJECT_TEMPLATE.format(
                            extra=extras,
                            entari_version=ENTARI_VERSION,
                            python_requirement=f'">= {info.major}.{info.minor}"',
                        )
                    )
            if check_package_installed("arclet-entari", python_path, local=True):
                print(f"{Fore.YELLOW}{i18n_.commands.init.messages.initialized()}{Fore.RESET}")
            else:
                ret_code = install_dependencies(
                    CommandLine.current().get_plugin(SelfSetting),  # type: ignore
                    [f"arclet.entari[{extras}]"],
                    python_path,
                    args,
                )
                if ret_code != 0:
                    return
            with toml_file.open("a+", encoding="utf-8") as f:
                f.seek(0)
                proj = tomlkit.load(f)
                entari_version = get_package_version("arclet-entari", python_path) or ENTARI_VERSION
                set_item(proj, "project.dependencies", [f"arclet.entari[{extras}] >= {entari_version}"])
                f.truncate(0)
                tomlkit.dump(proj, f)
            with create_config(result.query[str]("cfg_path.path"), is_dev):
                pass
            return
        return next_(None)
