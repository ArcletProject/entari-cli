from typing import Any

from tomlkit import TOMLDocument, table
from tomlkit.items import AoT, InlineTable, String, Table


def print_flattened(doc):
    def walk(tbl, path):
        for k, v in tbl.items():
            if isinstance(v, (Table, InlineTable)):
                yield from walk(v, path + [k])
            elif isinstance(v, AoT):
                for i, t in enumerate(v):
                    yield from walk(t, path + [f"{k}[{i}]"])
            else:
                yield ".".join(path + [k]), v

    for key, item in walk(doc, []):
        # 字符串去掉引号输出；其他类型用 TOML 表示
        val = item.value if isinstance(item, String) else item.as_string()
        yield key, val


def get_item(doc: TOMLDocument, key: str) -> Any:
    keys = key.split(".")
    current = doc
    for k in keys:
        if k in current:  # type: ignore
            current = current[k]  # type: ignore
        else:
            return None
    return current


def set_item(doc: TOMLDocument, key: str, value):
    keys = key.split(".")
    current = doc
    for k in keys[:-1]:
        current = current.setdefault(k, table())
    current[keys[-1]] = value


def del_item(doc: TOMLDocument, key: str):
    keys = key.split(".")
    current = doc
    for k in keys[:-1]:
        if k in current:  # type: ignore
            current = current[k]  # type: ignore
        else:
            return
    if keys[-1] in current:  # type: ignore
        del current[keys[-1]]  # type: ignore


DEFAULT: dict[str, Any] = {
    "editor": "",
    "install.package_manager": "",
    "install.command": "",
    "install.args": "",
    "uninstall.args": "",
}
