"""Run the student app as a macOS LaunchAgent: starts at login, restarts after a crash.

Paths come from the machine at install time; nothing personal is kept in the code.
"""

from __future__ import annotations

import os
import plistlib
import re
import ssl
import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PREFIX = "com.lerni."  # com.lerni.prod, com.lerni.dev

Runner = Callable[..., Any]


class ServiceError(Exception):
    """Something the admin can fix: said in one plain line."""


@dataclass(frozen=True)
class Server:
    """One server's settings, as `lerni serve` takes them."""

    name: str  # "prod" or "dev"
    port: int
    label: str  # shown on every page; "" for production
    data: Path | None  # LERNI_STUDENT_DATA, or None for the default
    cert: Path
    key: Path


def agent_label(name: str) -> str:
    """The launchd label for this server, e.g. ``com.lerni.prod``."""
    return PREFIX + name


def log_path(home: Path, name: str) -> Path:
    """Where this server's output goes."""
    return home / "Library" / "Logs" / "lerni" / f"{name}.log"


def agent_path(home: Path, name: str) -> Path:
    """Where this server's LaunchAgent lives."""
    return home / "Library" / "LaunchAgents" / f"{agent_label(name)}.plist"


def plist(server: Server, lerni: Path, checkout: Path, path_env: str, home: Path) -> bytes:
    """The LaunchAgent for this server, as a property list."""
    args = [str(lerni), "serve", "--port", str(server.port)]
    args += ["--label", server.label] if server.label else []
    args += ["--cert", str(server.cert), "--key", str(server.key)]
    env = {"PATH": path_env}  # so claude and whisper-cli are found
    if server.data is not None:
        env["LERNI_STUDENT_DATA"] = str(server.data)
    log = str(log_path(home, server.name))
    return plistlib.dumps(
        {
            "Label": agent_label(server.name),
            "ProgramArguments": args,
            "EnvironmentVariables": env,
            "WorkingDirectory": str(checkout),
            "RunAtLoad": True,
            "KeepAlive": True,  # restart after a crash
            "ThrottleInterval": 10,  # at most one restart every 10 seconds
            "LimitLoadToSessionType": "Aqua",  # the desktop session: say needs it
            "StandardOutPath": log,
            "StandardErrorPath": log,
        }
    )


def _uid(uid: int | None) -> int:
    return os.getuid() if uid is None else uid


def install(
    server: Server,
    run: Runner = subprocess.run,
    home: Path | None = None,
    lerni: Path | None = None,
    checkout: Path | None = None,
    path_env: str | None = None,
    uid: int | None = None,
    wait: float = 1.0,
) -> Path:
    """Write the agent and load it, replacing one already loaded.

    Returns:
        The property list's path.

    Raises:
        ServiceError: Development without its own data, no ``lerni`` to run, or macOS refused.
    """
    home = home or Path.home()
    if server.name == "dev" and server.data in (None, home / ".lerni" / "student"):
        raise ServiceError("Development needs its own data folder (--data), never production's.")
    lerni = lerni or Path(sys.executable).parent / "lerni"  # this checkout's own venv
    if not lerni.is_file():  # launchd would retry it forever
        raise ServiceError(f"No lerni at {lerni}: run this checkout's .venv/bin/lerni.")
    # the checkout root for an editable install (src/lerni/student/ -> root)
    checkout = checkout or Path(__file__).resolve().parents[3]
    path = agent_path(home, server.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path_env = os.environ.get("PATH", "") if path_env is None else path_env
    path.write_bytes(plist(server, lerni, checkout, path_env, home))
    label = f"gui/{_uid(uid)}/{agent_label(server.name)}"
    run(["launchctl", "bootout", label], capture_output=True)  # an older one; "not loaded" is fine
    log = log_path(home, server.name)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("")  # a fresh log, once the old one has stopped writing
    for _ in range(3):  # right after a bootout, launchd can still be unloading it
        try:
            run(["launchctl", "bootstrap", f"gui/{_uid(uid)}", str(path)], check=True)
            return path
        except subprocess.CalledProcessError:
            time.sleep(wait)
    raise ServiceError(
        f"macOS wouldn't start {agent_label(server.name)}: "
        "check you're logged in at the Mac, then install again."
    )


def restart(name: str, run: Runner = subprocess.run, uid: int | None = None) -> None:
    """Stop the server and start it again, on whatever code its checkout now holds.

    Raises:
        ServiceError: It isn't installed.
    """
    try:
        run(["launchctl", "kickstart", "-k", f"gui/{_uid(uid)}/{agent_label(name)}"],
            check=True, capture_output=True)
    except subprocess.CalledProcessError:
        raise ServiceError(
            f"{name} isn't running as a service yet: run lerni service install {name} first."
        ) from None


def stop(name: str, run: Runner = subprocess.run, uid: int | None = None) -> None:
    """Unload the agent until the next install or login (the file stays)."""
    run(["launchctl", "bootout", f"gui/{_uid(uid)}/{agent_label(name)}"], capture_output=True)


def uninstall(
    name: str, run: Runner = subprocess.run, uid: int | None = None, home: Path | None = None
) -> None:
    """Unload the agent and delete it; nothing starts at login any more."""
    stop(name, run, uid)
    agent_path(home or Path.home(), name).unlink(missing_ok=True)


def _listener(port: int) -> int | None:
    """The pid listening on this port, if any."""
    out = subprocess.run(
        ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"], capture_output=True, text=True
    ).stdout.split()
    return int(out[0]) if out else None


def _answers(port: int) -> bool:
    """Whether the sign-in page answers on this port (any certificate)."""
    context = ssl.create_default_context()
    context.check_hostname, context.verify_mode = False, ssl.CERT_NONE  # localhost, any cert
    try:
        with urllib.request.urlopen(
            f"https://localhost:{port}/signin", timeout=3, context=context
        ) as response:
            return response.status == 200
    except OSError:
        return False


def status(
    name: str, run: Runner = subprocess.run, uid: int | None = None, home: Path | None = None
) -> str:
    """One line: running and answering, loaded but not answering, or not installed."""
    home = home or Path.home()
    path = agent_path(home, name)
    if not path.is_file():
        return f"{name}: not installed"
    args = plistlib.loads(path.read_bytes())["ProgramArguments"]
    port = int(args[args.index("--port") + 1])
    shown = run(
        ["launchctl", "print", f"gui/{_uid(uid)}/{agent_label(name)}"],
        capture_output=True,
        text=True,
    )
    pid = re.search(r"\bpid = (\d+)", shown.stdout or "")
    # the agent itself must hold the port: a copy in a Terminal window doesn't count
    if pid and _listener(port) == int(pid.group(1)) and _answers(port):
        return f"{name}: running (pid {pid.group(1)}), answering on :{port}"
    return f"{name}: not answering on :{port}; see {log_path(home, name)}"
