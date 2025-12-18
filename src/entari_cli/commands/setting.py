from collections.abc import Mapping
import os
import subprocess
from typing import Any, Literal, overload

from arclet.alconna import Alconna, Args, Arparma, CommandMeta, Option
from clilte import BasePlugin, PluginMetadata, register
from clilte.core import Next
from colorama.ansi import Fore, Style, code_to_chars
from platformdirs import user_config_path
import tomlkit

from entari_cli import i18n_
from entari_cli.project import get_project_root
from entari_cli.setting import DEFAULT, del_item, get_item, print_flattened, set_item

ITALIC = code_to_chars(3)


def get_editor() -> str:
    for key in "VISUAL", "EDITOR":
        rv = os.getenv(key)
        if rv:
            return rv
    if os.name == "nt":
        return "start"
    for editor in "sensible-editor", "vim", "nano":
        if os.system(f"which {editor} >/dev/null 2>&1") == 0:
            return editor
    return "vi"


@register("entari_cli.plugins")
class SelfSetting(BasePlugin):
    def init(self):
        return Alconna(
            "setting",
            Args[f"key/?#{i18n_.commands.setting.key()}", str][f"value/#{i18n_.commands.setting.key()}", str, ""],
            Option("-l|--local", help_text=i18n_.commands.setting.options.local()),
            Option("-d|--delete", help_text=i18n_.commands.setting.options.delete()),
            Option("-e|--edit", help_text=i18n_.commands.setting.options.edit()),
            meta=CommandMeta(i18n_.commands.setting.description()),
        )

    def meta(self) -> PluginMetadata:
        return PluginMetadata(
            name="generate",
            description=i18n_.commands.setting.description(),
            version="0.1.0",
            priority=1,
        )

    @overload
    def get_setting(self, local: bool) -> "tomlkit.TOMLDocument | None": ...
    @overload
    def get_setting(self, local: bool, force: Literal[True]) -> tomlkit.TOMLDocument: ...

    def get_setting(self, local: bool, force=False):
        setting_dir = get_project_root() if local else user_config_path("entari-cli", appauthor=False)
        setting_file = setting_dir / (".entari_cli.toml" if local else "config.toml")
        if not setting_file.exists():
            if force:
                return tomlkit.document()
            return None
        with setting_file.open("r", encoding="utf-8") as f:
            return tomlkit.load(f)

    def save_setting(self, local: bool, config: tomlkit.TOMLDocument):
        setting_dir = get_project_root() if local else user_config_path("entari-cli", appauthor=False)
        setting_file = setting_dir / (".entari_cli.toml" if local else "config.toml")
        setting_dir.mkdir(parents=True, exist_ok=True)
        with setting_file.open("w+", encoding="utf-8") as f:
            tomlkit.dump(config, f)

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

    def set_config(self, key: str, value: Any, local: bool):
        cfg = self.get_setting(local, force=True)
        set_item(cfg, key, value)  # type: ignore
        self.save_setting(local, cfg)

    def dispatch(self, result: Arparma, next_: Next):
        if result.find("setting.edit"):
            if result.find("setting.args.key"):
                return f"{Fore.RED}{i18n_.commands.setting.edit.failed_key()}{Fore.RESET}"
            if result.find("setting.delete"):
                return f"{Fore.RED}{i18n_.commands.setting.edit.failed_delete()}{Fore.RESET}"
            setting_dir = (
                get_project_root() if result.find("setting.local") else user_config_path("entari-cli", appauthor=False)
            )
            setting_file = setting_dir / (".entari_cli.toml" if result.find("setting.local") else "config.toml")
            setting_dir.mkdir(parents=True, exist_ok=True)
            if not setting_file.exists():
                editor = get_editor()
            else:
                with setting_file.open("r", encoding="utf-8") as f:
                    doc = tomlkit.parse(f.read())
                    editor = get_item(doc, "editor") or get_editor()
            if " " in editor:
                editor = f'"{editor}"'
            proc = subprocess.Popen(f"{editor} {setting_file!s}", shell=False)
            if proc.wait() == 0:
                return
            return f"{Fore.RED}{i18n_.commands.setting.edit.failed(editor=editor)}{Fore.RESET}"
        if result.find("setting.delete"):
            key = result.query[str]("setting.args.key")
            if not key:
                return f"{Fore.RED}{i18n_.commands.setting.delete.missing()}{Fore.RESET}"
            cfg = self.get_setting(result.find("setting.local"))
            if not cfg:
                return f"{Fore.RED}{i18n_.commands.setting.delete.not_exist()}{Fore.RESET}"
            del_item(cfg, key)
            self.save_setting(result.find("setting.local"), cfg)
            return f"{Fore.GREEN}{i18n_.commands.setting.delete.success(key=key)}{Fore.RESET}"
        value = result.query[str]("setting.args.value", "")
        if value:
            key = result.query[str]("setting.args.key", "")
            setting_dir = (
                get_project_root() if result.find("setting.local") else user_config_path("entari-cli", appauthor=False)
            )
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
            return f"{Fore.GREEN}{i18n_.commands.setting.set.success(key=key, value=value)}{Fore.RESET}"
        if result.find("setting.args.key"):
            query = result.query[str]("setting.args.key", "")
            local_cfg = self.get_setting(True)
            global_cfg = self.get_setting(False)
            data = {
                **dict(print_flattened(global_cfg) if global_cfg else ()),
                **dict(print_flattened(local_cfg) if local_cfg else ()),
            }
            filtered = {key: DEFAULT[key] for key in DEFAULT if key.startswith(query)}
            filtered |= {key: data[key] for key in data if key.startswith(query)}
            if not filtered:
                return f"{Fore.RED}{i18n_.commands.setting.get_failed(query=query)}{Fore.RESET}"
            self._show_config(filtered, {})
            return
        if result.find("setting"):
            local_cfg = self.get_setting(True)
            global_cfg = self.get_setting(False)
            print(f"{Style.BRIGHT}{i18n_.commands.setting.list.title()}{Style.RESET_ALL}")
            self._show_config(
                DEFAULT,
                {
                    **dict(print_flattened(global_cfg) if global_cfg else ()),
                    **dict(print_flattened(local_cfg) if local_cfg else ()),
                },
            )
            if global_cfg:
                print(
                    f"\n{Style.BRIGHT}{i18n_.commands.setting.list.global_()} ({Fore.GREEN}{user_config_path('entari-cli', appauthor=False) / 'config.toml'}{Fore.RESET}){Style.RESET_ALL}"  # noqa: E501
                )
                self._show_config(dict(print_flattened(global_cfg)), {})
            if local_cfg:
                print(
                    f"\n{Style.BRIGHT}{i18n_.commands.setting.list.local()} ({Fore.GREEN}{get_project_root() / '.entari_cli.toml'}{Fore.RESET}){Style.RESET_ALL}"  # noqa: E501
                )
                self._show_config(dict(print_flattened(local_cfg)), {})
            return
        return next_(None)

    def _show_config(self, config: Mapping[str, Any], supersedes: Mapping[str, Any]):
        for key in sorted(config):
            superseded = key in supersedes
            if key.endswith(".password") or key.endswith(".token") or key.endswith(".secret"):
                value = f"{ITALIC}<hidden>"
            else:
                value = config[key]
                if value == "":
                    value = f"{ITALIC}<empty>{Fore.RESET}"
            print(f"{Style.DIM if superseded else ''}{Fore.CYAN}{key}{Fore.RESET} = {value}{Style.RESET_ALL}")
