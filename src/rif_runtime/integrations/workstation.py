"""Opt-in, bounded local host metadata collector (no external tool execution).

This module is a narrow read-only primitive, not an MCP server, authorization
broker, policy engine, or remote desktop controller. The API adapter owns
authentication and opt-in configuration.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import sys
from typing import TypedDict

ENABLED_VAR = "RIF_WORKSTATION_STATUS_ENABLED"
TARGET_VAR = "RIF_WORKSTATION_STATUS_TARGET"
_TARGET_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}\Z")


class WorkstationStatus(TypedDict):
    os_family: str
    python_version: str
    logical_cpu_count: int | None
    disk_total_bytes: int
    disk_free_bytes: int


def configured_target() -> str | None:
    """Return the explicitly configured local alias, otherwise disable the tool."""
    if os.environ.get(ENABLED_VAR, "").strip().lower() != "true":
        return None
    target = os.environ.get(TARGET_VAR, "").strip()
    if not _TARGET_RE.fullmatch(target):
        return None
    return target


def collect_local_status() -> WorkstationStatus:
    """Read a fixed set of OS counters without executing commands or using a network.

    Never return usernames, hostnames, file paths, process arguments, environment
    variables, credentials or arbitrary files. The filesystem query is fixed to
    the volume containing the process root; callers cannot provide paths.
    """
    family = platform.system()
    usage = shutil.disk_usage(os.path.abspath(os.sep))
    return {
        "os_family": family if family in {"Windows", "Linux", "Darwin"} else "other",
        "python_version": (
            f"{sys.version_info.major}.{sys.version_info.minor}."
            f"{sys.version_info.micro}"
        ),
        "logical_cpu_count": os.cpu_count(),
        "disk_total_bytes": usage.total,
        "disk_free_bytes": usage.free,
    }
