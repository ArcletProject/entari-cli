import importlib
import pkgutil

# import traceback
from clilte import CommandLine
from colorama.ansi import Fore

from .i18n import Lang

i18n_ = Lang.entari_cli

__version__ = "0.4.0"

cli = CommandLine(
    title="Entari CLI",
    version=__version__,
    rich=True,
    fuzzy_match=True,
    _name="entari",
    load_preset=False,
)


def printer(exc: Exception) -> None:
    print(f"{Fore.RED}[Error: {exc.__class__.__name__}]{Fore.RESET}: {exc!s}")
    # traceback.print_exception(type(exc), exc, exc.__traceback__)


cli.exception_printer = printer

COMMANDS_MODULE_PATH = importlib.import_module("entari_cli.commands").__path__

for _, name, _ in pkgutil.iter_modules(COMMANDS_MODULE_PATH):
    importlib.import_module(f"entari_cli.commands.{name}", __name__)
