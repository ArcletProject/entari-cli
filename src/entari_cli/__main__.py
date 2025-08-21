from entari_cli.commands.run import RunApplication
from entari_cli.commands.add import AddPlugin
from entari_cli.commands.remove import RemovePlugin
from entari_cli.commands.new import NewPlugin
from entari_cli.commands.generate import GenerateMain

from clilte import CommandLine


if __name__ == '__main__':
    cli = CommandLine(title="Entari CLI", version="0.1.0", rich=True, fuzzy_match=True)
    cli.add(NewPlugin, AddPlugin, RemovePlugin, RunApplication, GenerateMain)
    cli.main()
