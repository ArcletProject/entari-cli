from __future__ import annotations

import os
from pathlib import Path
import re

from colorama import Fore


def is_conda_base() -> bool:
    return os.getenv("CONDA_DEFAULT_ENV", "") == "base"


def is_conda_base_python(python: Path) -> bool:
    if not is_conda_base():
        return False
    prefix = os.environ["CONDA_PREFIX"]
    return is_path_relative_to(python, prefix)


def is_path_relative_to(path: str | Path, other: str | Path) -> bool:
    try:
        Path(path).relative_to(other)
    except ValueError:
        return False
    return True


def get_venv_like_prefix(interpreter: str | Path) -> tuple[Path | None, bool]:
    """Check if the given interpreter path is from a virtualenv,
    and return two values: the root path and whether it's a conda env.
    """
    interpreter = Path(interpreter)
    prefix = interpreter.parent
    if prefix.joinpath("conda-meta").exists():
        return prefix, True

    prefix = prefix.parent
    if prefix.joinpath("pyvenv.cfg").exists():
        return prefix, False
    if prefix.joinpath("conda-meta").exists():
        return prefix, True

    virtual_env = os.getenv("VIRTUAL_ENV")
    if virtual_env and is_path_relative_to(interpreter, virtual_env):
        return Path(virtual_env), False
    virtual_env = os.getenv("CONDA_PREFIX")
    if virtual_env and is_path_relative_to(interpreter, virtual_env):
        return Path(virtual_env), True
    return None, False


def find_python_in_path(path: str | Path) -> Path | None:
    """Find a python interpreter from the given path, the input argument could be:

    - A valid path to the interpreter
    - A Python root directory that contains the interpreter
    """
    pathlib_path = Path(path).absolute()
    if pathlib_path.is_file():
        return pathlib_path

    if os.name == "nt":
        for root_dir in (pathlib_path, pathlib_path / "Scripts"):
            if root_dir.joinpath("python.exe").exists():
                return root_dir.joinpath("python.exe")
    else:
        executable_pattern = re.compile(r"python(?:\d(?:\.\d+m?)?)?$")

        for python in pathlib_path.joinpath("bin").glob("python*"):
            if executable_pattern.match(python.name):
                return python

    return None


def ask(text: str, default=None):
    if default is not None:
        text += f" {Fore.MAGENTA}({default}){Fore.RESET}: "
        ans = input(text).strip() or default
    else:
        ans = input(f"{text}: {Fore.RESET}").strip()
    return ans
