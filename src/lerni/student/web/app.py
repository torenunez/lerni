"""Build the student app: a sign-in page and one Gradio app with tabs by role.

Signed-out visits go to ``/signin``; the app lives at ``/app/``. Gradio's
``auth_dependency`` re-checks the signed cookie on every request, and every
handler re-resolves the viewer. See the trust boundaries in
``docs/ARCHITECTURE.md``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Must be set before Gradio is imported: it also disables the version check.
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"

import gradio as gr  # noqa: E402
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import PlainTextResponse  # noqa: E402

from lerni.student.conversation import ChatModel, Conversations  # noqa: E402
from lerni.student.feedback import FeedbackStore  # noqa: E402
from lerni.student.interests import MapStore  # noqa: E402
from lerni.student.logs import ConversationLog  # noqa: E402
from lerni.student.signin import COOKIE_NAME, SignIn, load_secret  # noqa: E402
from lerni.student.students import StudentStore, default_data_dir  # noqa: E402
from lerni.student.tagging import MapKeeper, Tagger  # noqa: E402
from lerni.student.upload import Uploader  # noqa: E402
from lerni.student.web.main import build_main_view  # noqa: E402
from lerni.student.web.signin_page import APP_PATH, add_signin_routes  # noqa: E402

# Upload's 5 MB limit plus room for the form around the file.
MAX_UPLOAD_REQUEST = 5_000_000 + 64_000

# System fonts only, so the iPad never loads fonts from the internet.
_SYSTEM_FONTS = ("-apple-system", "system-ui", "Helvetica Neue", "Arial", "sans-serif")
_MONO_FONTS = ("ui-monospace", "Menlo", "monospace")

# The app's few style rules; everything else is Gradio's theme, all local.
_CSS = """
/* the chats' own trash icon is hidden: "New conversation" is the one way to start over */
#lerni-ask-chat button[aria-label="Clear"], #lerni-home-chat button[aria-label="Clear"] {
  display: none;
}
/* 16px text in fields, so iPhone Safari doesn't zoom in and shift the page on tap */
.gradio-container input, .gradio-container textarea { font-size: 16px !important; }
"""

# Settings for the mounted app: no footer links (that hides the API
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


def build_app(
    *,
    data_root: Path | None = None,
    chat_model: ChatModel | None = None,
    tagger: Tagger | None = None,
    uploader: Uploader | None = None,
    label: str = "",
    version: str = "",
) -> FastAPI:
    """Build the server: the sign-in page and the app at ``/app/``.

    Args:
        data_root: The home server's data folder; defaults to ``$LERNI_STUDENT_DATA``
            or ``~/.lerni/student``.
        chat_model: Claude behind an adapter for Ask Lerni; ``None`` turns it off.
        tagger: Claude behind an adapter for the map; ``None`` leaves maps unchanged
            (exchanges are still logged).
        uploader: Claude behind an adapter for Upload; ``None`` turns it off.
        label: Shown on every page, e.g. ``"Development"``; empty for production.
        version: Which code is running, shown small on the sign-in page.
    """
    root = data_root or default_data_dir()
    students = StudentStore(root)
    signin = SignIn(students, load_secret(root))
    # our own server; we turn off its docs pages too
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    add_signin_routes(app, signin, label, version)

    @app.middleware("http")
    async def limit_uploads(request: Request, call_next: Any) -> Any:
        # Gradio's own limit doesn't apply when it's mounted, so uploads are checked here
        if request.url.path.endswith("/gradio_api/upload"):
            size = request.headers.get("content-length", "")
            if not size.isdigit() or int(size) > MAX_UPLOAD_REQUEST:
                return PlainTextResponse("That file is too big (the limit is 5 MB).",
                                         status_code=413)
        return await call_next(request)

    def current_user(request: Request) -> str | None:
        # runs on every request: no valid cookie, no access
        viewer = signin.viewer_from_cookie(request.cookies.get(COOKIE_NAME))
        return viewer.username if viewer else None

    maps, log = MapStore(root), ConversationLog(root)
    log.purge()  # at startup; then once a day as exchanges are logged
    keeper = MapKeeper(maps, tagger, log)
    conversations = (
        Conversations(chat_model, context=keeper.context, on_exchange=keeper.after)
        if chat_model else None
    )
    view = build_main_view(
        signin, students, maps, conversations,
        uploader=uploader, feedback=FeedbackStore(root), model=chat_model, label=label,
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
