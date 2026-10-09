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

# The student screen's look. Everything is local: emoji built into the
# device and CSS animation, no images or web fonts. Motion stops when the
# device asks for reduced motion.
_CSS = """
.lerni-welcome {
  position: relative; overflow: hidden; border-radius: 28px;
  min-height: 78vh; display: flex; flex-direction: column;
  align-items: center; justify-content: center; text-align: center;
  padding: 2rem 1rem; color: #1b1340;
  background: linear-gradient(135deg, #ffe17a 0%, #ff9fb2 45%, #8fd3ff 100%);
}
.lerni-welcome h1 {
  font-size: clamp(2.6rem, 7vw, 4.5rem); margin: 0.2em 0; font-weight: 800;
  letter-spacing: -0.02em; animation: lerni-bounce 2.4s ease-in-out infinite;
}
.lerni-welcome p { font-size: clamp(1.4rem, 3.4vw, 2rem); margin: 0.3em 0; }
.lerni-welcome .lerni-wave { font-size: clamp(3rem, 9vw, 5.5rem); display: inline-block;
  animation: lerni-wave 2s ease-in-out infinite; transform-origin: 70% 70%; }
.lerni-welcome .lerni-ready {
  margin-top: 1.4em; padding: 0.6em 1.2em; border-radius: 999px;
  background: rgba(255, 255, 255, 0.75); font-size: clamp(1.2rem, 3vw, 1.6rem);
  font-weight: 700; animation: lerni-pulse 1.8s ease-in-out infinite;
}
.lerni-float { position: absolute; font-size: clamp(2.2rem, 6vw, 3.6rem);
  animation: lerni-float 7s ease-in-out infinite; opacity: 0.9; }
.lerni-float:nth-of-type(1) { top: 8%;  left: 7%;  animation-delay: 0s; }
.lerni-float:nth-of-type(2) { top: 14%; right: 9%; animation-delay: 1.2s; }
.lerni-float:nth-of-type(3) { bottom: 14%; left: 10%; animation-delay: 2.4s; }
.lerni-float:nth-of-type(4) { bottom: 9%; right: 8%; animation-delay: 0.6s; }
.lerni-float:nth-of-type(5) { top: 45%; left: 3%; animation-delay: 3s; }
.lerni-float:nth-of-type(6) { top: 42%; right: 3%; animation-delay: 1.8s; }
@keyframes lerni-float { 0%, 100% { transform: translateY(0) rotate(-6deg); }
  50% { transform: translateY(-18px) rotate(6deg); } }
@keyframes lerni-bounce { 0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); } }
@keyframes lerni-wave { 0%, 60%, 100% { transform: rotate(0deg); }
  15%, 45% { transform: rotate(16deg); } 30% { transform: rotate(-10deg); } }
@keyframes lerni-pulse { 0%, 100% { transform: scale(1); }
  50% { transform: scale(1.06); } }
@media (prefers-reduced-motion: reduce) {
  .lerni-welcome *, .lerni-welcome { animation: none !important; }
}
"""

# The student's waiting screen. The icons hint at the kinds of things there
# are to explore; they are decoration, so screen readers skip them.
_WELCOME_HTML = """
<div class="lerni-welcome" role="main">
  <span class="lerni-float" aria-hidden="true">🚗</span>
  <span class="lerni-float" aria-hidden="true">🦈</span>
  <span class="lerni-float" aria-hidden="true">⚽</span>
  <span class="lerni-float" aria-hidden="true">🚀</span>
  <span class="lerni-float" aria-hidden="true">🦖</span>
  <span class="lerni-float" aria-hidden="true">🔭</span>
  <span class="lerni-wave" aria-hidden="true">👋</span>
  <h1>Get ready to explore!</h1>
  <p>Cool questions about the things you love are coming.</p>
  <p class="lerni-ready">Waiting for your educator to start…</p>
</div>
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
    """The iPad screen. For now it greets the student and waits for the educator."""
    with gr.Blocks(title="Lerni", analytics_enabled=False) as blocks:
        gr.HTML(_WELCOME_HTML)
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
