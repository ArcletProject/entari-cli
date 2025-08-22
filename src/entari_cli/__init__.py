import importlib
import pkgutil

from clilte import CommandLine

from .i18n import Lang

i18n_ = Lang.entari_cli

__version__ = "0.1.0"

cli = CommandLine(
    title="Entari CLI",
    version=__version__,
    rich=True,
    fuzzy_match=True,
    _name="entari",
    load_preset=False,
)

COMMANDS_MODULE_PATH = importlib.import_module("entari_cli.commands").__path__

for _, name, _ in pkgutil.iter_modules(COMMANDS_MODULE_PATH):
    importlib.import_module(f"entari_cli.commands.{name}", __name__)
