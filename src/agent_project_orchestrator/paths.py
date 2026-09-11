from __future__ import annotations
import os, re
from pathlib import Path, PureWindowsPath

_WINDOWS_ABS = re.compile(r"^[A-Za-z]:[\\/]")


def path_key(value: str | os.PathLike[str], platform: str | None = None) -> str:
    """Return a comparison key stable across slash styles.

    On Windows-style paths drive letter/case are normalized and separators become '/'.
    On native POSIX paths we normalize/resolve non-strictly.
    """
    s = os.fspath(value)
    is_win = platform == "windows" or (platform is None and (_WINDOWS_ABS.match(s) or s.startswith("\\\\")))
    if is_win:
        p = PureWindowsPath(s)
        return p.as_posix().casefold().rstrip("/")
    p = Path(s).expanduser().resolve(strict=False)
    return os.path.normcase(str(p)).replace("\\", "/").rstrip("/")


def same_path(a: str | os.PathLike[str], b: str | os.PathLike[str], platform: str | None = None) -> bool:
    if platform is None:
        try:
            return os.path.samefile(a, b)
        except (OSError, ValueError):
            pass
    return path_key(a, platform=platform) == path_key(b, platform=platform)
