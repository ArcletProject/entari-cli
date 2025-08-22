from __future__ import annotations

from arclet.alconna import Arparma, Option
from clilte import BasePlugin, CommandLine, PluginMetadata, register

from entari_cli import i18n_


@register("entari_cli.plugins")
class Version(BasePlugin):
    def init(self):
        return Option("--version|-V", help_text=i18n_.commands.version.description()), False

    def dispatch(self, result: Arparma, next_):
        if result.find("version"):
            return CommandLine.current().version
        return next_(None)

    def meta(self) -> PluginMetadata:
        return PluginMetadata("version", "0.1.0", "version", ["version"], ["RF-Tar-Railt"], 0)
