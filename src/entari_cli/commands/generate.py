from pathlib import Path

from clilte import BasePlugin, PluginMetadata
from arclet.alconna import Alconna, Arparma, CommandMeta
from clilte.core import Next

from entari_cli.template import MAIN_SCRIPT


class GenerateMain(BasePlugin):
    def init(self):
        return Alconna(
            "gen_main",
            meta=CommandMeta("生成一个 Entari 主程序文件")
        )

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="generate",
            description="生成一个 Entari 主程序文件",
            version="0.1.0",
        )

    def dispatch(self, result: Arparma, next_: Next):
        if result.find("run"):
            file = Path.cwd() / "main.py"
            path = result.query[str]("cfg_path.path", "")
            with file.open("w+", encoding="utf-8") as f:
                f.write(MAIN_SCRIPT.format(path=f'"{path}"'))
            return f"Main script generated at {file}"
        return next_(None)
