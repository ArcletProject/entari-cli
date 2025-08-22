from __future__ import annotations

from collections.abc import Iterable
import dataclasses as dc
from functools import cached_property
from pathlib import Path
import shutil
import subprocess
import sys

from colorama import Fore
from findpython import BaseProvider, PythonVersion

from entari_cli import i18n_
from entari_cli.consts import WINDOWS
from entari_cli.utils import get_venv_like_prefix

BIN_DIR = "Scripts" if WINDOWS else "bin"


def get_venv_python(cwd: Path | None = None) -> tuple[Path, Path]:
    """Get the interpreter path inside the given venv."""
    cwd = (cwd or Path.cwd()).resolve()
    suffix = ".exe" if WINDOWS else ""
    venv = cwd / ".venv"
    for venv_dir in cwd.iterdir():
        if venv_dir.is_dir() and (venv_dir / "pyvenv.cfg").is_file():
            venv = venv_dir
            break
    result = venv / BIN_DIR / f"python{suffix}"
    if WINDOWS and not result.exists():
        result = venv / "bin" / f"python{suffix}"  # for mingw64/msys2
        if result.exists():
            return result, venv
        else:
            return venv / "python.exe", venv  # for conda
    return result, venv


def is_conda_venv(root: Path) -> bool:
    return (root / "conda-meta").exists()


@dc.dataclass(frozen=True)
class VirtualEnv:
    root: Path
    is_conda: bool
    interpreter: Path

    @classmethod
    def get(cls, cwd: Path) -> VirtualEnv | None:
        path, root = get_venv_python(cwd)
        if not path.exists():
            return None
        return cls(root, is_conda_venv(root), path)

    @classmethod
    def from_interpreter(cls, interpreter: Path) -> VirtualEnv | None:
        root, is_conda = get_venv_like_prefix(interpreter)
        if root is not None:
            return cls(root, is_conda, interpreter)
        return None

    def env_vars(self) -> dict[str, str]:
        key = "CONDA_PREFIX" if self.is_conda else "VIRTUAL_ENV"
        return {key: str(self.root)}

    @cached_property
    def venv_config(self) -> dict[str, str]:
        venv_cfg = self.root / "pyvenv.cfg"
        if not venv_cfg.exists():
            return {}
        parsed: dict[str, str] = {}
        with venv_cfg.open(encoding="utf-8") as fp:
            for line in fp:
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if k == "include-system-site-packages":
                        v = v.lower()
                    parsed[k] = v
        return parsed

    @property
    def include_system_site_packages(self) -> bool:
        return self.venv_config.get("include-system-site-packages") == "true"

    # @cached_property
    # def base_paths(self) -> list[str]:
    #     home = Path(self.venv_config["home"])
    #     base_executable = find_python_in_path(home) or find_python_in_path(home.parent)
    #     assert base_executable is not None
    #     paths = get_sys_config_paths(str(base_executable))
    #     return [paths["purelib"], paths["platlib"]]


def get_in_project_venv(cwd: Path) -> VirtualEnv | None:
    """Get the python interpreter path of venv-in-project"""
    venv = VirtualEnv.get(cwd)
    if venv is not None:
        return venv
    return None


class VenvProvider(BaseProvider):
    """A Python provider for project venv pythons"""

    def __init__(self, cwd: Path) -> None:
        self.cwd = cwd

    @classmethod
    def create(cls):
        return None

    def find_pythons(self) -> Iterable[PythonVersion]:
        in_project_venv = get_in_project_venv(self.cwd)
        if in_project_venv is not None:
            yield PythonVersion(
                in_project_venv.interpreter, _interpreter=in_project_venv.interpreter, keep_symlink=True
            )


try:
    import virtualenv
except ImportError:
    virtualenv = None


def _ensure_clean(location: Path, force: bool = False) -> None:
    if not location.exists():
        return
    if location.is_dir() and not any(location.iterdir()):
        return
    if not force:
        raise ValueError(f"The location {location} is not empty.")
    if location.is_file():
        location.unlink()
    else:
        for child in location.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()


def create_virtualenv(venv_dir: Path, base_python: str, prompt: str | None = None):
    _ensure_clean(venv_dir, force=True)
    prompt_option = (f"--prompt={prompt}",) if prompt else ()
    if virtualenv:
        cmd = [sys.executable, "-m", "virtualenv", str(venv_dir), "--python", base_python, *prompt_option]
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL)
    else:
        cmd = [base_python, "-m", "venv", str(venv_dir), *prompt_option]
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL)
    print(f"{Fore.GREEN}{i18n_.venv.create(venv_python=f'{Fore.YELLOW}{venv_dir.resolve()}')}{Fore.RESET}")
    return venv_dir
