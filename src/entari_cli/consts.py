import os
import sys

REQUIRES_PYTHON = (3, 9)
WINDOWS = sys.platform.startswith("win") or (sys.platform == "cli" and os.name == "nt")
DEFAULT_PYTHON = ("python3", "python")
WINDOWS_DEFAULT_PYTHON = ("python",)
