from pathlib import Path
import sys

from arclet.alconna import Alconna, Args, Arparma, CommandMeta, MultiVar, Option
from clilte import BasePlugin, PluginMetadata, register
from clilte.core import Next
from colorama import Fore

from entari_cli import i18n_
from entari_cli.config import EntariConfig
from entari_cli.process import call_pip
from entari_cli.project import PYTHON_VERSION, get_user_email_from_git, sanitize_project_name, validate_project_name
from entari_cli.py_info import PythonInfo, check_package_installed, iter_interpreters
from entari_cli.template import (
    PLUGIN_DEFAULT_TEMPLATE,
    PLUGIN_PROJECT_TEMPLATE,
    PLUGIN_STATIC_TEMPLATE,
    README_TEMPLATE,
)
from entari_cli.utils import is_conda_base_python
from entari_cli.venv import create_virtualenv, get_venv_like_prefix, get_venv_python


@register("entari_cli.plugins")
class NewPlugin(BasePlugin):
    def init(self):
        return Alconna(
            "new",
            Args["name/?", str],
            Option("-S|--static", help_text=i18n_.commands.new.options.static()),
            Option("-A|--application", help_text=i18n_.commands.new.options.application()),
            Option("-f|--file", help_text=i18n_.commands.new.options.file()),
            Option("-D|--disabled", help_text=i18n_.commands.new.options.disabled()),
            Option("-O|--optional", help_text=i18n_.commands.new.options.optional()),
            Option("-p|--priority", Args["num/", int], help_text=i18n_.commands.new.options.priority()),
            Option("-py|--python", Args["path/", str], help_text=i18n_.commands.new.options.python()),
            Option("--pip-args", Args["params/", MultiVar(str)], help_text=i18n_.commands.new.options.pip_args()),
            meta=CommandMeta(i18n_.commands.new.description()),
        )

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="new",
            description=i18n_.commands.new.description(),
            version="0.1.0",
        )

    def ask(self, text: str, default=None):
        if default is not None:
            text += f" {Fore.MAGENTA}({default}){Fore.RESET}: "
            ans = input(text).strip() or default
        else:
            ans = input(f"{text}: {Fore.RESET}").strip()
        return ans

    def select_python(self, cwd: Path, python: str) -> PythonInfo:

        def version_matcher(py_version: PythonInfo) -> bool:
            return py_version.valid

        python = python.strip()
        found_interpreters = list(dict.fromkeys(iter_interpreters(cwd, python, filter_func=version_matcher)))
        if not found_interpreters:
            raise ValueError(i18n_.commands.new.messages.no_python_found())

        print(i18n_.commands.new.prompts.select_python())
        for i, py_version in enumerate(found_interpreters):
            print(
                f"{i:>2}. {Fore.GREEN}{py_version.implementation}@{py_version.identifier}{Fore.RESET} ({py_version.path!s})"
            )
        selection = self.ask(i18n_.commands.new.prompts.please_select(), default="0")
        if not selection.isdigit() or int(selection) < 0 or int(selection) >= len(found_interpreters):
            raise ValueError(i18n_.commands.new.messages.invalid_selection())
        return found_interpreters[int(selection)]

    def ensure_python(self, python: str = "") -> PythonInfo:
        selected_python = self.select_python(Path.cwd(), python)
        if selected_python.get_venv() is None or is_conda_base_python(selected_python.path):
            venv_path = create_virtualenv(Path.cwd() / ".venv", str(selected_python.path))
            selected_python = PythonInfo.from_path(get_venv_python(venv_path)[0])
        return selected_python

    def dispatch(self, result: Arparma, next_: Next):
        if result.find("new"):
            is_application = result.find("new.application")
            python = result.query[str]("new.python.path", "")
            if not is_application:
                ans = self.ask(i18n_.commands.new.prompts.is_plugin_project(), "Y/n").strip().lower()
                is_application = ans in {"no", "false", "f", "0", "n", "n/a", "none", "nope", "nah"}
            if not is_application:
                args = result.query[tuple[str, ...]]("new.pip_args.params", ())
                if get_venv_like_prefix(sys.executable)[0] is None:
                    python_path = self.ensure_python(python).executable
                    ret_code = call_pip(str(python_path), "install", "arclet-entari[full]", *args)
                    if ret_code != 0:
                        return f"{Fore.RED}{i18n_.commands.new.messages.install_failed()}{Fore.RESET}"
                elif not check_package_installed("arclet.entari"):
                    ret_code = call_pip(sys.executable, "install", "arclet-entari[full]", *args)
                    if ret_code != 0:
                        return f"{Fore.RED}{i18n_.commands.new.messages.install_failed()}{Fore.RESET}"
            name = result.query[str]("new.name")
            if not name:
                name = self.ask(i18n_.commands.new.prompts.plugin_name())
            if not validate_project_name(name):
                return f"{Fore.RED}{i18n_.commands.new.messages.invalid(name=repr(name))}{Fore.RESET}"
            proj_name = sanitize_project_name(name).replace(".", "-").replace("_", "-")
            if not proj_name.lower().startswith("entari-plugin-") and not is_application:
                print(f"{Fore.RED}{i18n_.commands.new.messages.corrected(name=proj_name)}{Fore.RESET}")
                print(
                    f"{Fore.YELLOW}{i18n_.commands.new.messages.keep(opt=f'{Fore.MAGENTA}-A|--application')}{Fore.RESET}"
                )
                proj_name = f"entari-plugin-{proj_name}"
            file_name = proj_name.replace("-", "_")
            version = self.ask(i18n_.commands.new.prompts.plugin_version(), "0.1.0")
            description = self.ask(i18n_.commands.new.prompts.plugin_description())
            git_user, git_email = get_user_email_from_git()
            author = self.ask(i18n_.commands.new.prompts.plugin_author_name(), git_user)
            email = self.ask(i18n_.commands.new.prompts.plugin_author_email(), git_email)
            if not is_application:
                default_python_requires = f">={PYTHON_VERSION[0]}.{PYTHON_VERSION[1]}"
                python_requires = self.ask(i18n_.commands.new.prompts.python_requires(), default_python_requires)
                licence = self.ask(i18n_.commands.new.prompts.license(), "MIT")
            else:
                python_requires = ""
                licence = ""
            is_file = result.find("new.file")
            if not is_file:
                ans = self.ask(i18n_.commands.new.prompts.is_single_file(), "Y/n").strip().lower()
                is_file = ans in {"yes", "true", "t", "1", "y", "yea", "yeah", "yep", "sure", "ok", "okay", "", "y/n"}
            is_static = result.find("new.static")
            if not is_static:
                ans = self.ask(i18n_.commands.new.prompts.is_disposable(), "Y/n").strip().lower()
                is_static = ans in {"no", "false", "f", "0", "n", "n/a", "none", "nope", "nah"}
            if proj_name.startswith("entari-plugin-") and check_package_installed(file_name):
                return f"{Fore.RED}{i18n_.commands.new.messages.installed(name=proj_name)}{Fore.RESET}"
            path = Path.cwd() / ("plugins" if is_application else "src")
            path.mkdir(parents=True, exist_ok=True)
            if is_file:
                path = path.joinpath(f"{file_name}.py")
            else:
                path = path.joinpath(file_name, "__init__.py")
                path.parent.mkdir(exist_ok=True)
            with path.open("w+", encoding="utf-8") as f:
                t = PLUGIN_STATIC_TEMPLATE if is_static else PLUGIN_DEFAULT_TEMPLATE
                f.write(
                    t.format(
                        name=proj_name,
                        author=f'[{{"name": "{author}", "email": "{email}"}}]',
                        version=version,
                        description=description,
                    )
                )
            if not is_application:
                toml_path = Path.cwd() / "pyproject.toml"
                if not toml_path.exists():
                    with toml_path.open("w+", encoding="utf-8") as f:
                        f.write(
                            PLUGIN_PROJECT_TEMPLATE.format(
                                name=proj_name,
                                version=version,
                                description=description,
                                author=f'{{"name" = "{author}", "email" = "{email}"}}',
                                entari_version="0.15.0",
                                python_requirement=f'"{python_requires}"',
                                license=f'{{"text" = "{licence}"}}',
                            )
                        )
                readme_path = Path.cwd() / "README.md"
                if not readme_path.exists():
                    with readme_path.open("w+", encoding="utf-8") as f:
                        f.write(README_TEMPLATE.format(name=proj_name, description=description))
            cfg = EntariConfig.load(result.query[str]("cfg_path.path", None))
            if (
                file_name in cfg.plugin
                or f"entari_plugin_{file_name}" in cfg.plugin
                or file_name.removeprefix("entari_plugin_") in cfg.plugin
            ):
                return f"{Fore.RED}{i18n_.commands.new.messages.exists(name=file_name)}{Fore.RESET}"
            cfg.plugin[file_name] = {}
            if result.find("new.disabled"):
                cfg.plugin[file_name]["$disable"] = True
            if result.find("new.optional"):
                cfg.plugin[file_name]["$optional"] = True
            if result.find("new.priority"):
                cfg.plugin[file_name]["priority"] = result.query[int]("new.priority.num", 16)
            if is_application:
                cfg.basic.setdefault("external_dirs", []).append("plugins")
            cfg.save()
            return f"{Fore.GREEN}{i18n_.commands.new.messages.created(path=str(path))}{Fore.RESET}"
        return next_(None)
