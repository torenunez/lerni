"""Run the student app on the home server."""

from __future__ import annotations

import os

DEFAULT_PASSCODE_ENV = "LERNI_EDUCATOR_PASSCODE"


class MissingPasscodeError(RuntimeError):
    """The environment variable that should hold the passcode is unset or empty."""


def resolve_passcode(env_var: str = DEFAULT_PASSCODE_ENV) -> str:
    """Read the educator passcode from an environment variable.

    The passcode is never read from a file or a command-line argument, so it
    can't end up in the repository or in shell history.

    Args:
        env_var: Name of the environment variable holding the passcode.

    Returns:
        The passcode.

    Raises:
        MissingPasscodeError: If the variable is unset or empty.

    Example:
        >>> os.environ["DEMO_PASSCODE"] = "s3cret"
        >>> resolve_passcode("DEMO_PASSCODE")
        's3cret'
    """
    value = os.environ.get(env_var, "")
    if not value:
        raise MissingPasscodeError(
            f"Set the educator passcode first: export {env_var}='...'"
        )
    return value


def serve(host: str, port: int, passcode_env: str = DEFAULT_PASSCODE_ENV) -> None:
    """Start the student app and block until it stops.

    Args:
        host: Address to bind. ``0.0.0.0`` lets the iPad and the educator's
            device reach it on the home network.
        port: Port to listen on.
        passcode_env: Name of the environment variable holding the passcode.

    Raises:
        MissingPasscodeError: If the passcode variable is unset or empty.
    """
    passcode = resolve_passcode(passcode_env)

    import uvicorn

    from lerni.student.web.app import EDUCATOR_PATH, build_app

    app = build_app(passcode)
    print(f"Student screen:  http://<this-computer>:{port}/", flush=True)
    print(f"Educator view:   http://<this-computer>:{port}{EDUCATOR_PATH}/", flush=True)
    print("Home network only. Press Ctrl-C to stop.", flush=True)
    uvicorn.run(app, host=host, port=port, log_level="warning", access_log=False)
