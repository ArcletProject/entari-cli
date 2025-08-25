from entari_cli import cli

cli.load_entry()
cli.load_register("entari_cli.plugins")
cli.main("entari setting install.command add")
