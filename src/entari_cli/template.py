JSON_BASIC_TEMPLATE = """\
{
  "basic": {
    "network": [
      {
        "type": "websocket",
        "host": "127.0.0.1",
        "port": 5140,
        "path": "satori"
      }
    ],
    "ignore_self_message": true,
    "log": {
        "level": "info"
    },
    "prefix": ["/"]
  },
"""

JSON_PLUGIN_BLANK_TEMPLATE = """\
  "plugins": {{
{plugins}
  }}
}}
"""

JSON_PLUGIN_COMMON_TEMPLATE = """\
  "plugins": {
    ".record_message": {},
    "::echo": {},
    "::inspect": {}
  }
}
"""

JSON_PLUGIN_DEV_TEMPLATE = """\
  "plugins": {
    "$prelude": [
      "::auto_reload"
    ],
    ".record_message": {
      "record_send": true,
    },
    "::help": {},
    "::echo": {},
    "::inspect": {},
    "::auto_reload": {
      "watch_config": true
    }
  }
}
"""


YAML_BASIC_TEMPLATE = """\
basic:
  network:
    - type: websocket
      host: "127.0.0.1"
      port: 5140
      path: "satori"
  ignore_self_message: true
  log:
    level: "info"
  prefix: ["/"]
"""

YAML_PLUGIN_BLANK_TEMPLATE = """\
plugins:
{plugins}
"""


YAML_PLUGIN_COMMON_TEMPLATE = """\
plugins:
  .record_message: {}
  ::echo: {}
  ::inspect: {}
"""

YAML_PLUGIN_DEV_TEMPLATE = """\
plugins:
  $prelude:
    - ::auto_reload
  .record_message:
    record_send: true
  ::echo: {}
  ::help: {}
  ::inspect: {}
  ::auto_reload:
    watch_config: true
"""

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
    "arclet.entari >= {entari_version}",
]
requires-python = {python_requirement}
readme = "README.md"
license = {license}
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
