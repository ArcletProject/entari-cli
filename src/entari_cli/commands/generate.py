from pathlib import Path

from arclet.alconna import Alconna, Arparma, CommandMeta
from clilte import BasePlugin, PluginMetadata, register
from clilte.core import Next

from entari_cli import i18n_
from entari_cli.template import MAIN_SCRIPT


@register("entari_cli.plugins")
class GenerateMain(BasePlugin):
    def init(self):
        return Alconna("gen_main", meta=CommandMeta(i18n_.commands.generate.description()))

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="generate",
            description=i18n_.commands.generate.description(),
            version="0.1.0",
        )

    def dispatch(self, result: Arparma, next_: Next):
        if result.find("gen_main"):
            file = Path.cwd() / "main.py"
            path = result.query[str]("cfg_path.path", "")
            with file.open("w+", encoding="utf-8") as f:
                f.write(MAIN_SCRIPT.format(path=f'"{path}"'))
            return i18n_.commands.generate.messages.generated(file=str(file))
        return next_(None)
