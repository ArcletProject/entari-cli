import os
import sys

REQUIRES_PYTHON = (3, 10)
WINDOWS = sys.platform.startswith("win") or (sys.platform == "cli" and os.name == "nt")
DEFAULT_PYTHON = ("python3", "python")
WINDOWS_DEFAULT_PYTHON = ("python",)
ENTARI_VERSION = "0.16.5"

YES = {"yes", "true", "t", "1", "y", "yea", "yeah", "yep", "sure", "ok", "okay", "", "y/n"}
NO = {"no", "false", "f", "0", "n", "n/a", "none", "nope", "nah"}
