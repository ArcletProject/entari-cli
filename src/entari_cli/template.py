PLUGIN_DEFAULT_TEMPLATE = """\
from arclet.entari import metadata

metadata(
    name="{name}",
    author={author},
    version="{version}",
    description="{description}",
)
"""


PLUGIN_STATIC_TEMPLATE = """\
from arclet.entari import declare_static, metadata

metadata(
    name="{name}",
    author={author},
    version="{version}",
    description="{description}",
)
declare_static()
"""

PLUGIN_PROJECT_TEMPLATE = """\
[project]
name = "{name}"
version = "{version}"
description = "{description}"
authors = [
    {author}
]
dependencies = [
    "arclet.entari[yaml,cron,reload,dotenv] >= {entari_version}",
]
requires-python = {python_requirement}
readme = "README.md"
license = {license}
"""

WORKSPACE_PROJECT_TEMPLATE = """\
[project]
name = "entari-workspace"
version = "0.0.0"
description = ""
dependencies = [
    "arclet.entari[{extra}] >= {entari_version}",
]
requires-python = {python_requirement}
"""

README_TEMPLATE = """\
# {name}
{description}
"""

MAIN_SCRIPT = """\
from arclet.entari import Entari

app = Entari.load({path})
app.run()
"""
