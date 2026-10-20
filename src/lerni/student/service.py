"""Run the student app as a macOS LaunchAgent: starts at login, restarts after a crash.

Paths come from the machine at install time; nothing personal is kept in the code.
"""

from __future__ import annotations

import os
import plistlib
import re
import shutil
import ssl
import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PREFIX = "com.lerni."  # com.lerni.prod, com.lerni.dev
PORTS = {"prod": 7860, "dev": 7861}  # neither server may take the other's port
ROTATE_BYTES = 5_000_000  # a log this big moves to <name>.log.1 on restart
WAIT_SECONDS = 75  # longer than a failed start's 30 s retry plus a cold start
NOT_LOADED = 113  # launchctl's exit code for a service it doesn't know
DATA_ENV = "LERNI_STUDENT_DATA"  # set only from --data, never from the shell

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


def plist(server: Server, lerni: Path, checkout: Path, path_env: str, home: Path,
          settings: Mapping[str, str] | None = None) -> bytes:
    """The LaunchAgent for this server, as a property list, with Lerni's ``settings``."""
    args = [str(lerni), "serve", "--port", str(server.port)]
    args += ["--label", server.label] if server.label else []
    args += ["--cert", str(server.cert), "--key", str(server.key)]
    env = {"PATH": path_env}  # so claude and whisper-cli are found
    env.update({k: v for k, v in (settings or {}).items() if k != DATA_ENV})  # voice, models
    if server.data is not None:
        env[DATA_ENV] = str(server.data)
    log = str(log_path(home, server.name))
    return plistlib.dumps(
        {
            "Label": agent_label(server.name),
            "ProgramArguments": args,
            "EnvironmentVariables": env,
            "WorkingDirectory": str(checkout),
            "RunAtLoad": True,
            "KeepAlive": True,  # restart after a crash
            "ThrottleInterval": 30,  # a start that keeps failing retries every 30 seconds
            "LimitLoadToSessionType": "Aqua",  # the desktop session: say needs it
            "StandardOutPath": log,
            "StandardErrorPath": log,
        }
    )


def _same_folder(a: Path, b: Path) -> bool:
    """Whether two paths are one folder, through symlinks and any letter case (APFS)."""
    try:
        return os.path.samefile(a, b)
    except OSError:  # one doesn't exist yet: compare the resolved spelling
        return str(a.expanduser().resolve()).casefold() == str(b.expanduser().resolve()).casefold()


def _check_setup(server: Server, home: Path) -> None:
    """Refuse a server that would use the other one's data or port."""
    prod_data, dev_data = home / ".lerni" / "student", home / ".lerni" / "student-dev"
    if server.name == "dev" and (server.data is None or _same_folder(server.data, prod_data)):
        raise ServiceError("Development needs its own data folder (--data), never production's.")
    if server.name == "prod" and server.data is not None and _same_folder(server.data, dev_data):
        raise ServiceError("Production can't use development's data folder.")
    other = "dev" if server.name == "prod" else "prod"
    if server.port == PORTS[other]:
        raise ServiceError(f"Port {server.port} is {other}'s; pick another.")


def setup_warnings(server: Server, checkout: Path, path_env: str,
                   run: Runner = subprocess.run) -> list[str]:
    """Things that would quietly go wrong once it runs: lines to show, nothing refused."""
    warned = [f"{tool} isn't on the PATH saved for it, so {what} will be off: install from "
              "a Terminal on this Mac, not over SSH."
              for tool, what in (("claude", "Claude"), ("whisper-cli", "Hold to talk"))
              if shutil.which(tool, path=path_env) is None]
    if server.name == "prod":
        try:
            code = run(["git", "-C", str(checkout), "merge-base", "--is-ancestor", "HEAD",
                        "origin/main"], capture_output=True).returncode
        except OSError:
            code = 128  # no git here
        if code == 1:
            warned.append("This checkout holds code that isn't on main: production should "
                          "run only what's merged.")
        elif code:
            warned.append("Couldn't check this checkout is on main (git or origin/main missing).")
    return warned


def agent_settings(home: Path, name: str) -> dict[str, str]:
    """The settings in this server's agent file now, or none."""
    try:
        return dict(plistlib.loads(agent_path(home, name).read_bytes())["EnvironmentVariables"])
    except (OSError, plistlib.InvalidFileException, KeyError, TypeError, ValueError):
        return {}


def settings_note(before: Mapping[str, str], after: Mapping[str, str]) -> str:
    """Which Lerni settings an install saved, and which it dropped from the last one."""
    saved = sorted(k for k in after if k.startswith("LERNI_") and k != DATA_ENV)
    dropped = sorted(k for k in before if k.startswith("LERNI_") and k != DATA_ENV
                     and k not in after)
    note = f"Settings saved: {', '.join(saved) or 'none'}."
    return note + (f" Dropped (not in this shell): {', '.join(dropped)}." if dropped else "")


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
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Write the agent and load it, replacing one already loaded.

    Returns:
        The property list's path.

    Raises:
        ServiceError: Development without its own data, no ``lerni`` to run, or macOS refused.
    """
    home = home or Path.home()
    _check_setup(server, home)
    lerni = lerni or Path(sys.executable).parent / "lerni"  # this checkout's own venv
    if not lerni.is_file():  # launchd would retry it forever
        raise ServiceError(f"No lerni at {lerni}: run this checkout's .venv/bin/lerni.")
    # the checkout root for an editable install (src/lerni/student/ -> root)
    checkout = checkout or Path(__file__).resolve().parents[3]
    path = agent_path(home, server.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path_env = os.environ.get("PATH", "") if path_env is None else path_env
    shell = os.environ if environ is None else environ
    settings = {k: v for k, v in shell.items() if k.startswith("LERNI_")}
    path.write_bytes(plist(server, lerni, checkout, path_env, home, settings))
    label = f"gui/{_uid(uid)}/{agent_label(server.name)}"
    run(["launchctl", "bootout", label], capture_output=True)  # an older one; "not loaded" is fine
    log = log_path(home, server.name)
    log.parent.mkdir(parents=True, exist_ok=True)
    if log.is_file():  # a fresh log, keeping the last one: it may say why it failed
        log.replace(log.with_name(log.name + ".1"))
    for _ in range(3):  # right after a bootout, launchd can still be unloading it
        try:
            run(["launchctl", "bootstrap", f"gui/{_uid(uid)}", str(path)], check=True,
                capture_output=True)  # launchctl's own error once, not three times
            return path
        except subprocess.CalledProcessError:
            time.sleep(wait)
    raise ServiceError(
        f"macOS wouldn't start {agent_label(server.name)}: "
        "check you're logged in at the Mac, then install again."
    )


def _rotate(log: Path) -> None:
    """Move a big log aside; launchd opens a fresh one when it starts the server again."""
    if log.is_file() and log.stat().st_size > ROTATE_BYTES:
        log.replace(log.with_name(log.name + ".1"))


def restart(name: str, run: Runner = subprocess.run, uid: int | None = None,
            home: Path | None = None) -> None:
    """Stop the server and start it again, on whatever code its checkout now holds.

    Raises:
        ServiceError: It isn't installed.
    """
    home = home or Path.home()
    _rotate(log_path(home, name))
    try:
        run(["launchctl", "kickstart", "-k", f"gui/{_uid(uid)}/{agent_label(name)}"],
            check=True, capture_output=True)
        return
    except subprocess.CalledProcessError as exc:
        if exc.returncode != NOT_LOADED:  # loaded, but macOS refused: say so
            raise ServiceError(f"macOS wouldn't restart {name}; try lerni service restart "
                               f"{name} again, or see its log.") from None
    path = agent_path(home, name)
    if not path.is_file():
        raise ServiceError(
            f"{name} isn't running as a service yet: run lerni service install {name} first.")
    try:  # stopped earlier: start it again from its agent file
        run(["launchctl", "bootstrap", f"gui/{_uid(uid)}", str(path)], check=True,
            capture_output=True)
    except subprocess.CalledProcessError:
        raise ServiceError(f"macOS wouldn't start {name}: run lerni service install {name}.") \
            from None


def stop(name: str, run: Runner = subprocess.run, uid: int | None = None,
         sleep: Callable[[float], None] = time.sleep) -> bool:
    """Unload the agent until the next install or login (the file stays).

    Returns:
        Whether it was running.
    """
    target = f"gui/{_uid(uid)}/{agent_label(name)}"

    def loaded() -> bool:
        return run(["launchctl", "print", target], capture_output=True).returncode == 0

    was = loaded()
    run(["launchctl", "bootout", target], capture_output=True)
    for _ in range(20):  # launchd shows it loaded for a moment after bootout: wait it out
        if not loaded():
            return was
        sleep(0.25)
    raise ServiceError(f"{name} is still loaded; try lerni service stop {name} again.")


def wait_until_up(name: str, home: Path, check: Callable[[], str] | None = None,
                  sleep: Callable[[float], None] = time.sleep,
                  clock: Callable[[], float] = time.monotonic,
                  seconds: int = WAIT_SECONDS) -> str:
    """Wait for the server to answer; say why if it doesn't.

    Returns:
        The status line once it's running.

    Raises:
        ServiceError: Still not answering: the last log lines.
    """
    check = check or (lambda: status(name, home=home))
    deadline = clock() + seconds  # a check can take seconds itself: go by the clock
    while True:
        line = check()
        if ": running" in line:
            return line
        if clock() >= deadline:
            break
        sleep(1)
    log = log_path(home, name)
    tail = log.read_text(errors="replace").splitlines()[-10:] if log.is_file() else []
    raise ServiceError(f"{name} isn't answering after {seconds} seconds. The end of {log}:\n"
                       + "\n".join(tail))


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
    try:
        args = plistlib.loads(path.read_bytes())["ProgramArguments"]
        port = int(args[args.index("--port") + 1])
    except (plistlib.InvalidFileException, KeyError, ValueError, IndexError, TypeError):
        return f"{name}: its agent file can't be read; run lerni service install {name} again"
    shown = run(
        ["launchctl", "print", f"gui/{_uid(uid)}/{agent_label(name)}"],
        capture_output=True,
        text=True,
    )
    if shown.returncode != 0:
        return f"{name}: stopped (lerni service restart {name} starts it)"
    pid = re.search(r"\bpid = (\d+)", shown.stdout or "")
    # the agent itself must hold the port: a copy in a Terminal window doesn't count
    if pid and _listener(port) == int(pid.group(1)) and _answers(port):
        return f"{name}: running (pid {pid.group(1)}), answering on :{port}"
    return f"{name}: not answering on :{port}; see {log_path(home, name)}"
