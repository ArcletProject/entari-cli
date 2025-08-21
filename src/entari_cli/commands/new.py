from importlib.util import find_spec
from pathlib import Path

from clilte import BasePlugin, PluginMetadata
from arclet.alconna import Alconna, Arparma, CommandMeta, Args, Option, MultiVar
from clilte.core import Next
from colorama import Fore

from entari_cli.config import EntariConfig
from entari_cli.process import call_pip
from entari_cli.project import validate_project_name, get_user_email_from_git, PYTHON_VERSION, sanitize_project_name
from entari_cli.python import PythonInfo, iter_interpreters
from entari_cli.template import PLUGIN_DEFAULT_TEMPLATE, PLUGIN_STATIC_TEMPLATE, PLUGIN_PROJECT_TEMPLATE, README_TEMPLATE
from entari_cli.utils import is_conda_base_python
from entari_cli.venv import get_venv_python, create_virtualenv


class NewPlugin(BasePlugin):
    def init(self):
        return Alconna(
            "new",
            Args["name/?", str],
            Option("-S|--static", help_text="是否为静态插件"),
            Option("-A|--application", help_text="是否为应用插件"),
            Option("-f|--file", help_text="是否为单文件插件"),
            Option("-D|--disabled", help_text="是否插件初始禁用"),
            Option("-O|--optional", help_text="是否仅存储插件配置而不加载插件"),
            Option("-p|--priority", Args["num/", int], help_text="插件加载优先级"),
            Option("-py|--python", Args["path/", str], help_text="指定 Python 解释器路径"),
            Option("--pip-args", Args["params/", MultiVar(str)], help_text="传递给 pip 的额外参数"),
            meta=CommandMeta("新建一个 Entari 插件")
        )

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="new",
            description="新建一个 Entari 插件",
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
        found_interpreters = list(
            dict.fromkeys(iter_interpreters(cwd, python, filter_func=version_matcher))
        )
        if not found_interpreters:
            raise ValueError("No Python interpreter found.")

        print("Please enter the Python interpreter to use")
        for i, py_version in enumerate(found_interpreters):
            print(
                f"{i:>2}. {Fore.GREEN}{py_version.implementation}@{py_version.identifier}{Fore.RESET} ({py_version.path!s})"
            )
        selection = self.ask("Please select", default="0")
        if not selection.isdigit() or int(selection) < 0 or int(selection) >= len(found_interpreters):
            raise ValueError("Invalid selection.")
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
                ans = self.ask("Is this an plugin project?", "(Y/n)").strip().lower()
                is_application = ans in {"no", "false", "f", "0", "n", "n/a", "none", "nope", "nah"}
            if not is_application:
                args = result.query[tuple[str, ...]]("new.pip_args.params", ())
                python_info = self.ensure_python(python)
                ret_code = call_pip(str(python_info.executable), "install", "arclet-entari[full]", *args)
                if ret_code != 0:
                    return f"{Fore.RED}Failed to install arclet-entari[full] with pip, please check the output above.{Fore.RESET}"
            name = result.query[str]("new.name")
            if not name:
                name = self.ask("Plugin name")
            if not validate_project_name(name):
                return f"{Fore.RED}Invalid plugin name: {name!r} {Fore.RESET}"
            proj_name = sanitize_project_name(name).replace(".", "-").replace("_", "-")
            if not proj_name.lower().startswith("entari-plugin-") and not is_application:
                print(f"{Fore.RED}Plugin will be corrected to 'entari-plugin-{proj_name}' automatically.")
                print(
                    f"{Fore.YELLOW}If you want to keep the name, please use option {Fore.MAGENTA}-A|--application.{Fore.RESET}"
                )
                proj_name = f"entari-plugin-{proj_name}"
            file_name = proj_name.replace("-", "_")
            version = self.ask("Plugin version", "0.1.0")
            description = self.ask("Plugin description")
            git_user, git_email = get_user_email_from_git()
            author = self.ask("Plugin author name", git_user)
            email = self.ask("Plugin author email", git_email)
            if not is_application:
                default_python_requires = f">={PYTHON_VERSION[0]}.{PYTHON_VERSION[1]}"
                python_requires = self.ask("Python requires ('*' to allow any)", default_python_requires)
                licence = self.ask("License (SPDX name)", "MIT")
            else:
                python_requires = ""
                licence = ""
            is_file = result.find("new.file")
            if not is_file:
                ans = self.ask("Is this a single file plugin?", "(Y/n)").strip().lower()
                is_file = ans in {"yes", "true", "t", "1", "y", "yea", "yeah", "yep", "sure", "ok", "okay", "", "y/n"}
            is_static = result.find("new.static")
            if not is_static:
                ans = self.ask("Is this a disposable plugin?", "(Y/n)").strip().lower()
                is_static = ans in {"no", "false", "f", "0", "n", "n/a", "none", "nope", "nah"}
            if proj_name.startswith("entari-plugin-") and find_spec(file_name):
                return f"{Fore.RED}'{proj_name}' already installed, please use another name.{Fore.RESET}"
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
            if file_name in cfg.plugin or f"entari_plugin_{file_name}" in cfg.plugin or file_name.removeprefix("entari_plugin_") in cfg.plugin:
                return f"{Fore.RED}Plugin {file_name} already exists in the configuration file.{Fore.RESET}"
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
            return f"{Fore.GREEN}Plugin created at {path}.{Fore.RESET}"
        return next_(None)
