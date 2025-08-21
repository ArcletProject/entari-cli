import re
import shutil
import subprocess
import sys


PYTHON_VERSION = sys.version_info[:2]


def get_user_email_from_git() -> tuple[str, str]:
    """Get username and email from git config.
    Return empty if not configured or git is not found.
    """
    git = shutil.which("git")
    if not git:
        return "", ""
    try:
        username = subprocess.check_output([git, "config", "user.name"], text=True, encoding="utf-8").strip()
    except subprocess.CalledProcessError:
        username = ""
    try:
        email = subprocess.check_output([git, "config", "user.email"], text=True, encoding="utf-8").strip()
    except subprocess.CalledProcessError:
        email = ""
    return username, email


def validate_project_name(name: str) -> bool:
    """Check if the project name is valid or not"""

    pattern = r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$"
    return re.fullmatch(pattern, name, flags=re.IGNORECASE) is not None


def sanitize_project_name(name: str) -> str:
    """Sanitize the project name and remove all illegal characters"""
    pattern = r"[^a-zA-Z0-9\-_\.]+"
    result = re.sub(pattern, "-", name)
    result = re.sub(r"^[\._-]|[\._-]$", "", result)
    if not result:
        raise ValueError(f"Invalid project name: {name}")
    return result
