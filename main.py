from entari_cli import cli

cli.load_entry()
cli.load_register("entari_cli.plugins")
cli.main("entari setting --local abc.package_manager pdm")
