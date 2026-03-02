from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Optional

from colorama import Fore

from entari_cli import i18n_
from entari_cli.consts import REQUIRES_PYTHON
from entari_cli.process import run_process
from entari_cli.py_info import PythonInfo, iter_interpreters
from entari_cli.setting import set_item
from entari_cli.utils import ask, is_conda_base_python
from entari_cli.venv import create_virtualenv, get_venv_python

PYTHON_VERSION = sys.version_info[:2]
CHECK_PM_MAP = {
    "uv": "add",
    "pdm": "add",
    "poetry": "add",
    "rye": "add",
    "pip": "install",
    "pipenv": "install",
}
PM_REMOVE_MAP = {
    "uv": "remove",
    "pdm": "remove",
    "poetry": "remove",
    "rye": "remove",
    "pip": "uninstall",
    "pipenv": "uninstall",
}


if TYPE_CHECKING:
    from entari_cli.commands.setting import SelfSetting


def get_user_email_from_git() -> tuple[str, str]:
    """Get username and email from git config.
    Return empty if not configured or git is not found.
    """
    git = shutil.which("git")
    if not git:
        return "", ""
    try:
        username = subprocess.check_output([git, "config", "user.name"], text=True, encoding="utf-8").strip()
    except subprocess.CalledProcessError:
        username = ""
    try:
        email = subprocess.check_output([git, "config", "user.email"], text=True, encoding="utf-8").strip()
    except subprocess.CalledProcessError:
        email = ""
    return username, email


def validate_project_name(name: str) -> bool:
    """Check if the project name is valid or not"""

    pattern = r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$"
    return re.fullmatch(pattern, name, flags=re.IGNORECASE) is not None


def sanitize_project_name(name: str) -> str:
    """Sanitize the project name and remove all illegal characters"""
    pattern = r"[^a-zA-Z0-9\-_\.]+"
    result = re.sub(pattern, "-", name)
    result = re.sub(r"^[\._-]|[\._-]$", "", result)
    if not result:
        raise ValueError(f"Invalid project name: {name}")
    return result


def select_python(cwd: Path, python: str) -> PythonInfo:

    def version_matcher(py_version: PythonInfo) -> bool:
        return py_version.valid and py_version.minor >= REQUIRES_PYTHON[1]

    python = python.strip()
    found_interpreters = list(dict.fromkeys(iter_interpreters(cwd, python, filter_func=version_matcher)))
    if not found_interpreters:
        raise ValueError(i18n_.project.no_python_found())

    print(i18n_.project.select_python())
    for i, py_version in enumerate(found_interpreters):
        print(
            f"{i:>2}. {Fore.GREEN}{py_version.implementation}@{py_version.identifier}{Fore.RESET} ({py_version.path!s})"
        )
    selection = ask(i18n_.project.please_select(), default="0")
    if not selection.isdigit() or int(selection) < 0 or int(selection) >= len(found_interpreters):
        raise ValueError(i18n_.project.invalid_selection())
    return found_interpreters[int(selection)]


def ensure_python(cwd: Path, python: str = "") -> PythonInfo:
    selected_python = select_python(cwd, python)
    if selected_python.get_venv() is None or is_conda_base_python(selected_python.path):
        prompt = f"{cwd.name}-{selected_python.major}.{selected_python.minor}"
        create_virtualenv(cwd / ".venv", str(selected_python.path), prompt)
        selected_python = PythonInfo.from_path(get_venv_python(cwd)[0])
    return selected_python


def get_project_root() -> Path:
    """Get the root directory of the current project."""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "pyproject.toml").exists() or (parent / "setup.py").exists():
            return parent
    return cwd


def select_package_manager() -> tuple[str, str]:
    """Select a package manager from the available ones."""
    available_pms = []
    for pm in CHECK_PM_MAP:
        if executable := shutil.which(pm):
            available_pms.append((pm, executable))
    if not available_pms:
        return "pip", "install"
    print(i18n_.project.select_pm())
    for i, (pm, exe) in enumerate(available_pms):
        print(f"{i:>2}. {Fore.GREEN}{pm}{Fore.RESET} ({exe})")
    selection = ask(i18n_.project.please_select(), default="0")
    if not selection.isdigit() or int(selection) < 0 or int(selection) >= len(available_pms):
        raise ValueError(i18n_.project.invalid_selection())
    return available_pms[int(selection)][0], CHECK_PM_MAP[available_pms[int(selection)][0]]


def install_dependencies(
    setting: "SelfSetting",
    deps: list[str],
    python_path: Optional[str] = None,
    install_args: Optional[tuple[str, ...]] = None,
):
    """Install dependencies"""

    def call_pip(*args):
        return run_process(python_path or sys.executable, "-m", "pip", *args)

    pm = setting.get_config("install.package_manager")
    cmd = setting.get_config("install.command")
    if not pm:
        pm, cmd = select_package_manager()
        cfg = setting.get_setting(True, force=True)
        set_item(cfg, "install.package_manager", pm)  # type: ignore
        set_item(cfg, "install.command", cmd)  # type: ignore
        setting.save_setting(True, cfg)
    de_install_args = setting.get_config("install.args")
    install_args = install_args or ()
    if de_install_args:
        install_args = (*de_install_args.split(","), *install_args)
    if pm == "pip":
        ret_code = call_pip("install", *install_args, *deps)
    else:
        executable = shutil.which(pm)
        if not executable:
            print(f"{Fore.YELLOW}{i18n_.project.fallback_pip(pm=pm)}{Fore.RESET}")
            pm = "pip"
            ret_code = call_pip("install", *install_args, *deps)
        else:
            ret_code = run_process(executable, cmd, *install_args, *deps)
    if ret_code != 0:
        print(f"{Fore.RED}{i18n_.project.install_failed(deps=', '.join(deps), pm=pm)}{Fore.RESET}")
    return ret_code


def uninstall_dependencies(
    setting: "SelfSetting",
    deps: list[str],
    python_path: Optional[str] = None,
    uninstall_args: Optional[tuple[str, ...]] = None,
):
    def call_pip(*args):
        return run_process(python_path or sys.executable, "-m", "pip", *args)

    pm = setting.get_config("install.package_manager")
    if not pm:
        pm, cmd = select_package_manager()
        cfg = setting.get_setting(True, force=True)
        set_item(cfg, "install.package_manager", pm)  # type: ignore
        set_item(cfg, "install.command", cmd)  # type: ignore
        setting.save_setting(True, cfg)
    de_uninstall_args = setting.get_config("uninstall.args")
    uninstall_args = uninstall_args or ()
    if de_uninstall_args:
        uninstall_args = (*de_uninstall_args.split(","), *uninstall_args)
    if pm == "pip":
        ret_code = call_pip("uninstall", "-y", *uninstall_args, *deps)
    else:
        executable = shutil.which(pm)
        if not executable:
            print(f"{Fore.YELLOW}{i18n_.project.fallback_pip(pm=pm)}{Fore.RESET}")
            pm = "pip"
            ret_code = call_pip("uninstall", "-y", *uninstall_args, *deps)
        else:
            cmd = PM_REMOVE_MAP.get(pm, "uninstall")
            ret_code = run_process(executable, cmd, *uninstall_args, *deps)
    if ret_code != 0:
        print(f"{Fore.RED}{i18n_.project.uninstall_failed(deps=', '.join(deps), pm=pm)}{Fore.RESET}")
    return ret_code
