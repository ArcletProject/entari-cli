def main():
    from entari_cli import cli

    cli.load_register("entari_cli.plugins")
    cli.main()


if __name__ == "__main__":
    main()
