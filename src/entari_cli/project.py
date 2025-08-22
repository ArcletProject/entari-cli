from pathlib import Path
import re
import shutil
import subprocess
import sys

from colorama import Fore

from entari_cli import i18n_
from entari_cli.py_info import PythonInfo, iter_interpreters
from entari_cli.utils import ask, is_conda_base_python
from entari_cli.venv import create_virtualenv, get_venv_python

PYTHON_VERSION = sys.version_info[:2]


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
        return py_version.valid

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
