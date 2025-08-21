from pathlib import Path

from arclet.alconna import Alconna, Args, Arparma, CommandMeta, Option
from clilte import BasePlugin, PluginMetadata, register
from clilte.core import Next

from entari_cli.process import run_process
from entari_cli.python import get_default_python
from entari_cli.template import MAIN_SCRIPT


@register("entari_cli.plugins")
class RunApplication(BasePlugin):
    def init(self):
        return Alconna(
            "run",
            Option("-py|--python", Args["path/", str], help_text="自定义 Python 解释器路径"),
            meta=CommandMeta("运行 Entari"),
        )

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="run",
            description="运行 Entari 应用",
            version="0.1.0",
        )

    def dispatch(self, result: Arparma, next_: Next):
        if result.find("run"):
            python_path = result.query[str]("run.python") or get_default_python()
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
        return next_(None)
