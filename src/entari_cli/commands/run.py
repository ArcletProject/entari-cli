from pathlib import Path

from arclet.alconna import Alconna, Arparma, CommandMeta
from clilte import BasePlugin, PluginMetadata, register
from clilte.core import Next

from entari_cli import i18n_
from entari_cli.process import run_process
from entari_cli.py_info import get_default_python
from entari_cli.template import MAIN_SCRIPT


@register("entari_cli.plugins")
class RunApplication(BasePlugin):
    def init(self):
        return Alconna(
            "run",
            meta=CommandMeta(i18n_.commands.run.description()),
        )

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="run",
            description=i18n_.commands.run.description(),
            version="0.1.0",
        )

    def dispatch(self, result: Arparma, next_: Next):
        if result.find("run"):
            python_path = result.query[str]("run.python") or get_default_python(prompt=True)
            cwd = Path.cwd()
            if (cwd / "main.py").exists():
                ret_code = run_process(
                    python_path,
                    Path("main.py"),
                    cwd=cwd,
                )
            else:
                path = result.query[str]("cfg_path.path", "")
                ret_code = run_process(
                    python_path,
                    "-c",
                    MAIN_SCRIPT.format(path=f'"{path}"'),
                    cwd=cwd,
                )
            exit(ret_code)
        return next_(None)
