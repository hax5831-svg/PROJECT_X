"""Shared subprocess execution helpers.

Nearly every module that shells out to a system tool (wpctl, hyprctl,
playerctl, brightnessctl, upower, sensors, ip, feh, swww, ...) used to
duplicate the same try/except/timeout boilerplate independently. This
module centralizes the three shapes that boilerplate actually took:

  - run_query()    -- run a command, return its stdout on success or None
  - run_query_raw() -- same, but returns the full CompletedProcess for
                        callers that need the returncode/stderr too
  - run_action()   -- fire-and-forget a command, return whether it launched
  - run_detached() -- launch a long-lived process (e.g. a screen locker)
                       without waiting for it, return whether it launched

All of them swallow subprocess failures (missing binary, timeout,
permission errors) by design -- a missing optional CLI tool is an expected,
common case for this app, not a bug. But the failure is recorded via
hyprfetch.core.debug_log so it isn't silently invisible when you're
actually trying to debug a "why isn't X detected" issue.
"""

from __future__ import annotations

import subprocess
from typing import Optional, Sequence

from hyprfetch.core.debug_log import log_debug


def run_query(cmd: Sequence[str], timeout: float = 1.5) -> Optional[str]:
    """Run `cmd`, returning stripped stdout if it exits 0, else None."""
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        log_debug(f"run_query failed: {list(cmd)}: {e}")
        return None
    if res.returncode != 0:
        log_debug(f"run_query non-zero exit ({res.returncode}): {list(cmd)}")
        return None
    return res.stdout.strip()


def run_query_raw(cmd: Sequence[str], timeout: float = 1.5) -> Optional[subprocess.CompletedProcess]:
    """Like run_query, but returns the full CompletedProcess (for callers
    that need to inspect returncode/stdout/stderr separately) or None on
    any failure to launch/complete the command.
    """
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        log_debug(f"run_query_raw failed: {list(cmd)}: {e}")
        return None


def run_action(cmd: Sequence[str], timeout: float = 1.0) -> bool:
    """Fire-and-forget a command. Returns True if it launched and ran to
    completion without raising, regardless of its exit code -- this matches
    the pre-existing behavior across the codebase, where callers only cared
    whether the command could be *invoked* at all (e.g. best-effort volume,
    brightness, or media control), not whether the target daemon liked it.
    """
    try:
        subprocess.run(cmd, check=False, timeout=timeout)
        return True
    except Exception as e:
        log_debug(f"run_action failed: {list(cmd)}: {e}")
        return False


def run_detached(cmd: Sequence[str]) -> bool:
    """Launch a long-lived process (e.g. a screen locker) without waiting
    for it to exit. Returns whether it launched successfully.
    """
    try:
        subprocess.Popen(cmd)
        return True
    except Exception as e:
        log_debug(f"run_detached failed: {list(cmd)}: {e}")
        return False
