"""Fresh path checks for historical reads without repeated metadata queries.

The frozen workspace path policy remains authoritative. Its successful ordinary
path case needs one non-following metadata record per ancestor; suspicious paths,
custom observers and filesystem errors retain the frozen compatibility behavior.
No filesystem result or validated-ancestor flag is retained between checks.
"""

import os
import re
import stat
from pathlib import Path, PureWindowsPath

from otarchguard.diagnostics import fail
from otarchguard.evidence.workspace import _local

_PATH_TYPE = type(Path())


def _observers() -> tuple[object, ...]:
    """Resolved observers, including concrete-class overrides on Windows."""
    return (
        _PATH_TYPE.stat,
        _PATH_TYPE.lstat,
        _PATH_TYPE.is_symlink,
        _PATH_TYPE.is_junction,
        os.stat,
        os.lstat,
        os.path.islink,
        getattr(os.path, "isjunction", None),
    )


_NATIVE_OBSERVERS = _observers()


def _check_read_path(path: Path) -> None:
    """Check each path component from one fresh lstat, never a cached result."""
    # A custom Path or replaced observation API may have intentionally different
    # semantics. Let the unchanged policy handle those cases in full. These are
    # function references, not cached path/stat/validation results.
    if type(path) is not _PATH_TYPE or not all(
        current is native for current, native in zip(_observers(), _NATIVE_OBSERVERS, strict=True)
    ):
        _local(path)
        return
    if str(path).startswith(("\\\\", "//")) or PureWindowsPath(path).drive.startswith("\\\\"):
        _local(path)
        return
    absolute = path.absolute()
    for name in absolute.parts[1:]:
        if (
            name in {".", ".."}
            or name.endswith((".", " "))
            or any(c in name for c in '\\:*?<>|"')
            or any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in name)
            or re.fullmatch(r"(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?", name)
        ):
            _local(path)
            return
    for part in (absolute, *absolute.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        except OSError:
            # Path.is_symlink has different OSError policies on supported Python
            # versions. Keep their established diagnostics rather than invent a
            # version-dependent interpretation here.
            _local(path)
            return
        reparse = getattr(info, "st_file_attributes", 0) & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
        )
        if (
            stat.S_ISLNK(info.st_mode)
            or reparse
            and getattr(info, "st_reparse_tag", 0)
            in {
                getattr(stat, "IO_REPARSE_TAG_SYMLINK", 0xA000000C),
                getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003),
            }
        ):
            # Never retry away an unsafe condition already observed, even if a
            # concurrent filesystem change would make a later query look safe.
            fail("EVIDENCE_PATH", "$", "Evidence paths must not traverse links or junctions.")
        if reparse:
            fail("EVIDENCE_PATH", "$", "Evidence paths must not traverse reparse points.")
