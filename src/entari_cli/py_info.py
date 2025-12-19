from __future__ import annotations

from collections.abc import Iterable
from functools import cached_property
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Callable

from colorama import Fore
from packaging.version import InvalidVersion, Version

from entari_cli import i18n_
from entari_cli.consts import DEFAULT_PYTHON, WINDOWS, WINDOWS_DEFAULT_PYTHON
from entari_cli.utils import find_python_in_path
from entari_cli.venv import VirtualEnv, get_venv_python

if TYPE_CHECKING:
    from findpython import Finder, PythonVersion


PYENV_ROOT = Path.expanduser(Path(os.getenv("PYENV_ROOT", "~/.pyenv")))


def _get_env_python() -> str:
    python_to_try = WINDOWS_DEFAULT_PYTHON if WINDOWS else DEFAULT_PYTHON

    stdout, stderr = None, None

    for python in python_to_try:
        proc = subprocess.Popen(
            f"{python} -W ignore -c " '"import sys, json; print(json.dumps(sys.executable))"',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate()
        if proc.returncode == 0:
            try:
                if executable := json.loads(stdout.splitlines()[-1].strip()):
                    return executable
            except Exception:
                continue
    raise RuntimeError(
        "Cannot find a valid Python interpreter."
        + (f"\nstdout:\n{stdout}" if stdout else "")
        + (f"\nstderr:\n{stderr}" if stderr else "")
    )


_path_venv_cache: dict[Path, str] = {}


def get_default_python(cwd: Path | None = None, prompt: bool = False) -> str:
    cwd = cwd or Path.cwd().resolve()

    if cwd in _path_venv_cache:
        return _path_venv_cache[cwd]

    venv_python, _ = get_venv_python(cwd)
    if venv_python.exists():
        _path_venv_cache[cwd] = str(venv_python)
        if prompt:
            print(f"{Fore.GREEN}{i18n_.venv.use(venv_python=str(venv_python))}{Fore.RESET}")
        return str(venv_python)

    return _get_env_python()


class PythonInfo:
    """
    A convenient helper class that holds all information of a Python interpreter.
    """

    def __init__(self, py_version: PythonVersion) -> None:
        self._py_ver = py_version

    @classmethod
    def from_path(cls, path: str | Path) -> PythonInfo:
        from findpython import PythonVersion

        py_ver = PythonVersion(Path(path))
        return cls(py_ver)

    @cached_property
    def valid(self) -> bool:
        return self._py_ver.executable.exists() and self._py_ver.is_valid()

    def __hash__(self) -> int:
        return hash(self._py_ver)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, PythonInfo):
            return False
        return self.path == o.path

    @property
    def path(self) -> Path:
        return self._py_ver.executable

    @property
    def executable(self) -> Path:
        return self._py_ver.interpreter

    @cached_property
    def version(self) -> Version:
        return self._py_ver.version

    @cached_property
    def implementation(self) -> str:
        return self._py_ver.implementation.lower()

    @property
    def major(self) -> int:
        return self.version.major

    @property
    def minor(self) -> int:
        return self.version.minor

    @property
    def micro(self) -> int:
        return self.version.micro

    @property
    def version_tuple(self) -> tuple[int, ...]:
        return (self.major, self.minor, self.micro)

    @property
    def is_32bit(self) -> bool:
        return "32bit" in self._py_ver.architecture

    def for_tag(self) -> str:
        return f"{self.major}{self.minor}"

    @property
    def identifier(self) -> str:
        try:
            version_str = f"{self.major}.{self.minor}"
        except InvalidVersion:
            return "unknown"

        if self._py_ver.freethreaded:
            version_str += "t"
        if os.name == "nt" and self.is_32bit:
            version_str += "-32"
        return version_str

    def get_venv(self) -> VirtualEnv | None:
        return VirtualEnv.from_interpreter(self.executable)


def get_python_finder(cwd: Path, search_venv: bool = True) -> Finder:
    from findpython import ALL_PROVIDERS, Finder

    from entari_cli.venv import VenvProvider

    providers: list[str] = ["venv", *ALL_PROVIDERS.keys()]
    venv_pos = -1
    if not providers:
        venv_pos = 0
    elif "venv" in providers:
        venv_pos = providers.index("venv")
        providers.remove("venv")
    finder = Finder(resolve_symlinks=True, selected_providers=providers or None)
    if search_venv and venv_pos >= 0:
        finder.add_provider(VenvProvider(cwd), venv_pos)
    return finder


def find_interpreters(
    cwd: Path, python_spec: str | None = None, search_venv: bool | None = None
) -> Iterable[PythonInfo]:
    """Return an iterable of interpreter paths that matches the given specifier,
    which can be:
        1. a version specifier like 3.7
        2. an absolute path
        3. a short name like python3
        4. None that returns all possible interpreters
    """
    python: str | Path | None = None
    finder_arg: str | None = None

    if not python_spec:
        if PYENV_ROOT.exists():
            pyenv_shim = PYENV_ROOT.joinpath("shims", "python3")
            if os.name == "nt":
                pyenv_shim = pyenv_shim.with_suffix(".bat")
            if pyenv_shim.exists():
                yield PythonInfo.from_path(pyenv_shim)
            elif pyenv_shim.with_name("python").exists():
                yield PythonInfo.from_path(pyenv_shim.with_name("python"))
        python = shutil.which("python") or shutil.which("python3")
        if python:
            yield PythonInfo.from_path(python)
    else:
        if not all(c.isdigit() for c in python_spec.split(".")):
            path = Path(python_spec)
            if path.exists():
                python = find_python_in_path(python_spec)
                if python:
                    yield PythonInfo.from_path(python)
                    return
            if len(path.parts) == 1:  # only check for spec with only one part
                python = shutil.which(python_spec)
                if python:
                    yield PythonInfo.from_path(python)
                    return
        finder_arg = python_spec
    if search_venv is None:
        search_venv = True
    finder = get_python_finder(cwd, search_venv)
    for entry in finder.find_all(finder_arg, allow_prereleases=True):
        yield PythonInfo(entry)
    if not python_spec:
        # Lastly, return the host Python as well
        this_python = getattr(sys, "_base_executable", sys.executable)
        yield PythonInfo.from_path(this_python)


def iter_interpreters(
    cwd: Path,
    python_spec: str | None = None,
    search_venv: bool | None = None,
    filter_func: Callable[[PythonInfo], bool] | None = None,
) -> Iterable[PythonInfo]:
    """Iterate over all interpreters that matches the given specifier.
    And optionally install the interpreter if not found.
    """

    found = False

    for interpreter in find_interpreters(cwd, python_spec, search_venv):
        if filter_func is None or filter_func(interpreter):
            found = True
            yield interpreter
    if found:
        return


def check_package_installed(
    package: str, python_path: str | None = None, cwd: Path | None = None, local: bool = False
) -> bool:
    executable = python_path or get_default_python(cwd)
    if local:
        script = f"""\
import json
import importlib.util
print(json.dumps(importlib.util.find_spec('{package}') is not None))
"""
    else:
        script = f"""\
import json
import importlib.metadata
try:
    importlib.metadata.distribution('{package}')
    print(json.dumps(True))
except importlib.metadata.PackageNotFoundError:
    print(json.dumps(False))
"""
    proc = subprocess.Popen(
        [executable, "-W", "ignore", "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, _ = proc.communicate()
    if proc.returncode == 0:
        try:
            return json.loads(stdout.splitlines()[-1].strip())
        except Exception:
            return False
    return False


def get_package_module(package: str, python_path: str | None = None, cwd: Path | None = None) -> str | None:
    executable = python_path or get_default_python(cwd)
    script = f"""\
import json
import importlib.util
import importlib.metadata

dist = importlib.metadata.distribution('{package}')
files = dist.files
if not files:
    print(json.dumps(None))
    exit(0)
importable = set()
for file in files:
    if file.suffix == '.py' or file.suffix == '.pyc':
        parts = file.parts
        if parts[-1] == '__init__.py' or parts[-1] == '__init__.pyc':
            importable.add('.'.join(parts[:-1]))
        else:
            importable.add('.'.join(parts).rsplit('.', 1)[0])
if not importable:
    print(json.dumps(None))
    exit(0)

importable = list(importable)
importable.sort(key=lambda x: len(x))

spec = None
for name in importable:
    spec = importlib.util.find_spec(name)
    if spec is not None:
        break
if spec is None or spec.origin is None:
    print(json.dumps(None))
    exit(0)
print(json.dumps(spec.name))
"""
    proc = subprocess.Popen(
        [executable, "-W", "ignore", "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, _ = proc.communicate()
    if proc.returncode == 0:
        try:
            return json.loads(stdout.splitlines()[-1].strip())
        except Exception:
            return None
    return None


def get_module_package(module: str, python_path: str | None = None, cwd: Path | None = None) -> str | None:
    executable = python_path or get_default_python(cwd)
    script = f"""\
import json
import importlib.util
import importlib.metadata
from pathlib import Path

spec = importlib.util.find_spec('{module}')
if spec is None or spec.origin is None:
    print(json.dumps(None))
    exit(0)
for dist in importlib.metadata.distributions(name="cli_lite"):
    relative_path = Path(spec.origin).relative_to(str(dist.locate_file(""))).as_posix()
    if relative_path in map(str, dist.files or []):
        break
else:
    print(json.dumps(None))
    exit(0)
print(json.dumps(dist.metadata['Name']))
"""
    proc = subprocess.Popen(
        [executable, "-W", "ignore", "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, _ = proc.communicate()
    if proc.returncode == 0:
        try:
            return json.loads(stdout.splitlines()[-1].strip())
        except Exception:
            return None


def get_package_version(package: str, python_path: str | None = None, cwd: Path | None = None) -> str | None:
    executable = python_path or get_default_python(cwd)
    script = f"""\
import json
import importlib.metadata
print(json.dumps(importlib.metadata.version('{package}')))
"""
    proc = subprocess.Popen(
        [executable, "-W", "ignore", "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, _ = proc.communicate()
    if proc.returncode == 0:
        try:
            return json.loads(stdout.splitlines()[-1].strip())
        except Exception:
            return None
    return None


if __name__ == "__main__":
    print(get_default_python(Path.cwd().parent.parent))
    print(check_package_installed("findpython"))
    print(get_package_version("findpytho"))
