import os
from pathlib import Path
import signal
import subprocess
import sys
from typing import Union


def run_process(
    *args: Union[str, bytes, "os.PathLike[str]", "os.PathLike[bytes]"],
    cwd: Union[Path, None] = None,
) -> int:
    """Run command in a subprocess and return the exit code."""

    def forward_signal(signum: int, frame) -> None:
        if sys.platform == "win32" and signum == signal.SIGINT:
            signum = signal.SIGTERM
        p.send_signal(signum)

    handle_term = signal.signal(signal.SIGTERM, forward_signal)
    handle_int = signal.signal(signal.SIGINT, forward_signal)
    p = subprocess.Popen(args, cwd=cwd, bufsize=0, close_fds=False)
    retcode = p.wait()
    signal.signal(signal.SIGTERM, handle_term)
    signal.signal(signal.SIGINT, handle_int)
    return retcode
