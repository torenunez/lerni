"""Build the student app: two Gradio apps on one server.

The student screen is mounted at ``/`` with no login. The educator view is a
separate app mounted at ``/educator`` behind the educator's passcode, so the
server checks the passcode for every educator request. See the trust
boundaries in ``docs/ARCHITECTURE.md``.
"""

from __future__ import annotations

import hmac
import os
from typing import TYPE_CHECKING

# Must be set before Gradio is imported: it also disables the version check.
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"

import gradio as gr  # noqa: E402
from fastapi import FastAPI  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Callable

EDUCATOR_PATH = "/educator"
EDUCATOR_USERNAME = "educator"

# System fonts only, so the iPad never loads fonts from the internet.
_SYSTEM_FONTS = ("-apple-system", "system-ui", "Helvetica Neue", "Arial", "sans-serif")
_MONO_FONTS = ("ui-monospace", "Menlo", "monospace")

# Large, calm text that reads well on an iPad.
_CSS = """
.lerni-big { font-size: 2.2rem; line-height: 1.3; text-align: center; padding: 3rem 1rem; }
"""

# Settings shared by both mounted apps: no footer links (that hides the API
# page link), no saved runs in the browser, no MCP server, no monitoring,
# client-side rendering (no Node server), and no extra file paths served.
_MOUNT_OPTIONS = {
    "footer_links": [],
    "run_history": False,
    "mcp_server": False,
    "enable_monitoring": False,
    "ssr_mode": False,
    # No API schema or docs pages on either app.
    "app_kwargs": {"openapi_url": None, "docs_url": None, "redoc_url": None},
}


def _theme() -> gr.themes.Base:
    """Return a theme that uses only fonts already on the device."""
    return gr.themes.Base(font=_SYSTEM_FONTS, font_mono=_MONO_FONTS)


def passcode_checker(passcode: str) -> Callable[[str, str], bool]:
    """Return a login check for the educator view.

    Args:
        passcode: The educator's passcode. Must not be empty.

    Returns:
        A function Gradio calls with the typed username and password. It
        accepts only the username ``educator`` and the exact passcode, using a
        constant-time comparison.

    Raises:
        ValueError: If ``passcode`` is empty.

    Example:
        >>> check = passcode_checker("s3cret")
        >>> check("educator", "s3cret"), check("educator", "guess")
        (True, False)
    """
    if not passcode:
        raise ValueError("the educator passcode must not be empty")
    expected = passcode.encode("utf-8")

    def check(username: str, password: str) -> bool:
        user_ok = hmac.compare_digest(username.encode("utf-8"), EDUCATOR_USERNAME.encode())
        pass_ok = hmac.compare_digest(password.encode("utf-8"), expected)
        return user_ok and pass_ok

    return check


def _student_screen() -> gr.Blocks:
    """The iPad screen. For now it only waits for the educator to start."""
    with gr.Blocks(title="Lerni", analytics_enabled=False) as blocks:
        gr.Markdown("Waiting for your educator to start.", elem_classes="lerni-big")
    return blocks


def _educator_view() -> gr.Blocks:
    """The educator's screen. The activity list arrives in Release 1 step 2."""
    with gr.Blocks(title="Lerni: educator view", analytics_enabled=False) as blocks:
        gr.Markdown("## Educator view")
        gr.Markdown("No approved activities yet.")
    return blocks


def build_app(passcode: str) -> FastAPI:
    """Build the server with the student screen and the educator view.

    Args:
        passcode: The educator's passcode, already resolved from the
            environment by the caller. Must not be empty.

    Returns:
        A FastAPI app with the educator view at ``/educator`` (passcode
        required) and the student screen at ``/`` (no login).

    Raises:
        ValueError: If ``passcode`` is empty.
    """
    check = passcode_checker(passcode)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    # Mount the educator view first so "/" doesn't swallow its path.
    app = gr.mount_gradio_app(
        app,
        _educator_view(),
        path=EDUCATOR_PATH,
        auth=check,
        auth_message="Enter the username <b>educator</b> and your passcode.",
        theme=_theme(),
        css=_CSS,
        **_MOUNT_OPTIONS,
    )
    app = gr.mount_gradio_app(
        app,
        _student_screen(),
        path="/",
        theme=_theme(),
        css=_CSS,
        **_MOUNT_OPTIONS,
    )
    return app
