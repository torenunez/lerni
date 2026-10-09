"""Build the student app: a sign-in page and one Gradio app with tabs by role.

Signed-out visits go to ``/signin``; the app lives at ``/app/``. Gradio's
``auth_dependency`` re-checks the signed cookie on every request, and every
handler re-resolves the viewer. See the trust boundaries in
``docs/ARCHITECTURE.md``.
"""

from __future__ import annotations

import os
from pathlib import Path

# Must be set before Gradio is imported: it also disables the version check.
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"

import gradio as gr  # noqa: E402
from fastapi import FastAPI, Request  # noqa: E402

from lerni.student.catalog import PackageLessonCatalog  # noqa: E402
from lerni.student.plan_import import PlanDrafter  # noqa: E402
from lerni.student.plans import PlanStore, default_data_dir  # noqa: E402
from lerni.student.signin import COOKIE_NAME, SignIn, load_secret  # noqa: E402
from lerni.student.students import StudentStore  # noqa: E402
from lerni.student.web.main import build_main_view  # noqa: E402
from lerni.student.web.signin_page import APP_PATH, add_signin_routes  # noqa: E402

MIN_PASSCODE = 8

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


MIN_PASSCODE_MESSAGE = f"The educator passcode needs at least {MIN_PASSCODE} characters."


def build_app(
    passcode: str,
    *,
    data_root: Path | None = None,
    store: PlanStore | None = None,
    catalog: PackageLessonCatalog | None = None,
    drafter: PlanDrafter | None = None,
) -> FastAPI:
    """Build the server: the sign-in page and the app at ``/app/``.

    Args:
        passcode: The educator passcode, already read from the environment.
        data_root: The home server's data folder; defaults to ``$LERNI_STUDENT_DATA``
            or ``~/.lerni/student``.
        store: Learning plans; defaults to the plan folder under ``data_root``.
        catalog: Packaged activities; defaults to the ones shipped with Lerni.
        drafter: Claude behind an adapter for imports; ``None`` turns imports off.

    Raises:
        ValueError: The passcode is shorter than 8 characters.
    """
    if len(passcode) < MIN_PASSCODE:
        raise ValueError(MIN_PASSCODE_MESSAGE)
    root = data_root or default_data_dir()
    students = StudentStore(root)
    signin = SignIn(students, passcode, load_secret(root))
    # our own server; we turn off its docs pages too
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    add_signin_routes(app, signin)

    def current_user(request: Request) -> str | None:
        # runs on every request: no valid cookie, no access
        viewer = signin.viewer_from_cookie(request.cookies.get(COOKIE_NAME))
        return viewer.username if viewer else None

    view = build_main_view(
        signin, store or PlanStore(root), catalog or PackageLessonCatalog(), students, drafter
    )
    return gr.mount_gradio_app(
        app,
        view,
        path=APP_PATH,
        auth_dependency=current_user,
        theme=_theme(),
        css=_CSS,
        **_MOUNT_OPTIONS,
    )
