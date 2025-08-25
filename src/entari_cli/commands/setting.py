import os
import subprocess
from typing import Any, Mapping

import tomlkit
from arclet.alconna import Alconna, Arparma, CommandMeta, Option, Args
from clilte import BasePlugin, PluginMetadata, register
from clilte.core import Next
from colorama.ansi import Fore, Style, code_to_chars
from platformdirs import user_config_path

from entari_cli import i18n_
from entari_cli.project import get_project_root
from entari_cli.setting import DEFAULT, del_item, get_item, set_item, print_flattened


ITALIC = code_to_chars(3)


def get_editor() -> str:
    for key in "VISUAL", "EDITOR":
        rv = os.getenv(key)
        if rv:
            return rv
    if os.name == "nt":
        return "notepad"
    for editor in "sensible-editor", "vim", "nano":
        if os.system(f"which {editor} >/dev/null 2>&1") == 0:
            return editor
    return "vi"


@register("entari_cli.plugins")
class SelfSetting(BasePlugin):
    def init(self):
        return Alconna(
            "setting",
            Args["key/?#Config key", str]["value/?#Config value", str],
            Option("-l|--local", help_text="Set config in the  local configuration file"),
            Option("-d|--delete", help_text="Unset a configuration key"),
            Option("-e|--edit", help_text="Open the configuration file in the editor(defined by EDITOR env var)"),
            meta=CommandMeta("Display the entari-cli configuration")
        )

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="generate",
            description=i18n_.commands.generate.description(),
            version="0.1.0",
            priority=1,
        )

    def get_setting(self, local: bool):
        setting_dir = get_project_root() if local else user_config_path("entari-cli", appauthor=False)
        setting_file = setting_dir / (".entari_cli.toml" if local else "config.toml")
        if not setting_file.exists():
            return None
        with setting_file.open("r", encoding="utf-8") as f:
            return tomlkit.load(f)

    def get_config(self, key: str):
        value = None
        local_cfg = self.get_setting(True)
        global_cfg = self.get_setting(False)
        if local_cfg:
            value = get_item(local_cfg, key)
        if global_cfg and value is None:
            value = get_item(global_cfg, key)
        if value is None:
            return DEFAULT[key]
        return value

    def dispatch(self, result: Arparma, next_: Next):
        if result.find("setting.edit"):
            if result.find("setting.args.key"):
                return f"{Fore.RED}Cannot specify an argument when `--edit` is given{Fore.RESET}"
            if result.find("setting.delete"):
                return f"{Fore.RED}`--delete` doesn't work when `--edit` is given{Fore.RESET}"
            setting_dir = get_project_root() if result.find("setting.local") else user_config_path("entari-cli", appauthor=False)
            setting_file = setting_dir / (".entari_cli.toml" if result.find("setting.local") else "config.toml")
            setting_dir.mkdir(parents=True, exist_ok=True)
            editor = get_editor()
            proc = subprocess.Popen(f"{editor} {setting_file!s}", shell=True)

            if proc.wait() == 0:
                return f"{Fore.GREEN}Configuration file edited successfully.{Fore.RESET}"
            return f"{Fore.RED}Editor {editor} exited abnormally{Fore.RESET}"
        if result.find("setting.delete"):
            key = result.query[str]("setting.args.key")
            if not key:
                return f"{Fore.RED}Please specify the configuration key to unset{Fore.RESET}"
            setting_dir = get_project_root() if result.find("setting.local") else user_config_path("entari-cli", appauthor=False)
            setting_file = setting_dir / (".entari_cli.toml" if result.find("setting.local") else "config.toml")
            with setting_file.open("r", encoding="utf-8") as f:
                cfg = tomlkit.load(f)
            del_item(cfg, key)
            with setting_file.open("w", encoding="utf-8") as f:
                tomlkit.dump(cfg, f)
            return f"{Fore.GREEN}Configuration key '{key}' unset.{Fore.RESET}"
        if result.find("setting.args.value"):
            key = result.query[str]("setting.args.key")
            if not key:
                return f"{Fore.RED}Please specify the configuration key to unset{Fore.RESET}"
            value = result.query[str]("setting.args.value")
            setting_dir = get_project_root() if result.find("setting.local") else user_config_path("entari-cli", appauthor=False)
            setting_file = setting_dir / (".entari_cli.toml" if result.find("setting.local") else "config.toml")
            setting_dir.mkdir(parents=True, exist_ok=True)
            with setting_file.open("a+", encoding="utf-8") as f:
                f.seek(0)
                try:
                    cfg = tomlkit.load(f)
                except Exception:
                    cfg = tomlkit.document()
                set_item(cfg, key, value)  # type: ignore
                f.truncate(0)
                tomlkit.dump(cfg, f)
            return f"{Fore.GREEN}Configuration key '{key}' set to '{value}'.{Fore.RESET}"
        if result.find("setting.args.key"):
            query = result.query[str]("setting.args.key", "")
            local_cfg = self.get_setting(True)
            global_cfg = self.get_setting(False)
            lines = []
            if local_cfg:
                for key, value in print_flattened(local_cfg):
                    if not key.startswith(query):
                        continue
                    if key.endswith(".password") or key.endswith(".token") or key.endswith(".secret"):
                        value = f"{ITALIC}<hidden>{Fore.RESET}"
                    lines.append(f"{Fore.CYAN}{key}{Fore.RESET} = {value}")
                # value = get_item(local_cfg, key)
            if global_cfg:
                for key, value in print_flattened(global_cfg):
                    if not key.startswith(query):
                        continue
                    if key.endswith(".password") or key.endswith(".token") or key.endswith(".secret"):
                        value = f"{ITALIC}<hidden>{Fore.RESET}"
                    lines.append(f"{Fore.CYAN}{key}{Fore.RESET} = {value}")
            if not lines:
                return f"{Fore.RED}Configuration key '{query}' not found.{Fore.RESET}"
            return "\n".join(lines)
        if result.find("setting"):
            local_cfg = self.get_setting(True)
            global_cfg = self.get_setting(False)
            print(f"{Style.BRIGHT}Site/default setting{Style.RESET_ALL}")
            self._show_config(DEFAULT, {
                **dict(print_flattened(global_cfg) if global_cfg else ()),
                **dict(print_flattened(local_cfg) if local_cfg else ()),
            })
            if global_cfg:
                print(f"\n{Style.BRIGHT}Global configuration file ({Fore.GREEN}{user_config_path('entari-cli', appauthor=False) / 'config.toml'}{Fore.RESET}){Style.RESET_ALL}")
                self._show_config(dict(print_flattened(global_cfg)),{})
            if local_cfg:
                print(f"\n{Style.BRIGHT}Local configuration file ({Fore.GREEN}{get_project_root() / '.entari_cli.toml'}{Fore.RESET}){Style.RESET_ALL}")
                self._show_config(dict(print_flattened(local_cfg)),{})
            # lines = []
            # if local_cfg:
            #     lines.append(f"# Local Configuration File ({Fore.GREEN}{get_project_root() / '.entari_cli.toml'}{Fore.RESET})")
            #     for key, value in print_flattened(local_cfg):
            #         if key.endswith(".password") or key.endswith(".token") or key.endswith(".secret"):
            #             value = f"{ITALIC}<hidden>{Fore.RESET}"
            #         lines.append(f"{Fore.CYAN}{key}{Fore.RESET} = {value}")
            #     lines.append("")
            # if global_cfg:
            #     lines.append(f"# Global Configuration File ({Fore.GREEN}{user_config_path('entari-cli', appauthor=False) / 'config.toml'}{Fore.RESET})")
            #     for key, value in print_flattened(local_cfg):
            #         if key.endswith(".password") or key.endswith(".token") or key.endswith(".secret"):
            #             value = f"{ITALIC}<hidden>{Fore.RESET}"
            #         lines.append(f"{Fore.CYAN}{key}{Fore.RESET} = {value}")
            #     lines.append("")
            # return "\n".join(lines) if lines else f"{Fore.YELLOW}No configuration found.{Fore.RESET}"
        return next_(None)

    def _show_config(self, config: Mapping[str, Any], supersedes: Mapping[str, Any]):
        for key in sorted(config):
            superseded = key in supersedes
            if key.endswith(".password") or key.endswith(".token") or key.endswith(".secret"):
                value = f"{ITALIC}<hidden>"
            else:
                value = config[key]
            print(
                f"{Style.DIM if superseded else ''}{Fore.CYAN}{key}{Fore.RESET} = {value}{Style.RESET_ALL}"
            )
