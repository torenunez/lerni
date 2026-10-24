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
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse  # noqa: E402

from lerni.student.concepts import ConceptStore  # noqa: E402
from lerni.student.conversation import ChatModel, Conversations  # noqa: E402
from lerni.student.educator_agent import EducatorChats
from lerni.student.feedback import FeedbackStore  # noqa: E402
from lerni.student.garage import Garage  # noqa: E402
from lerni.student.interests import MapStore  # noqa: E402
from lerni.student.logs import ConversationLog  # noqa: E402
from lerni.student.points import PointsStore  # noqa: E402
from lerni.student.race import Quizzer, RaceDesk  # noqa: E402
from lerni.student.results import ResultsLog  # noqa: E402
from lerni.student.signin import SignIn, cookie_name, load_secret  # noqa: E402
from lerni.student.students import (  # noqa: E402
    AccountError,
    Kind,
    StudentStore,
    default_data_dir,
)
from lerni.student.tagging import MapKeeper, Tagger  # noqa: E402
from lerni.student.upload import Uploader  # noqa: E402
from lerni.student.usage import Usage  # noqa: E402
from lerni.student.voice import Speech  # noqa: E402
from lerni.student.web.games import SOUNDS  # noqa: E402
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
/* use the whole screen: thin margins, small gaps, a one-line header, bigger chat text */
.gradio-container { padding: 4px 8px !important; max-width: 100% !important;
  --layout-gap: 8px; }
.gradio-container .main { padding: 0 !important; }
.lerni-header { align-items: center !important; flex-wrap: nowrap !important; }
.lerni-header > * { flex: none !important; min-width: 0 !important; width: auto !important; }
.lerni-header > .lerni-title { flex: 1 !important; }
/* the menu replaces the tab bar: ☰ and the section's name, and a drawer from the left */
.tab-wrapper { display: none !important; }
.lerni-menu-btn { font-size: 26px; line-height: 1; padding: 4px 10px; background: none; }
.lerni-title p { font-size: 18px; margin: 0; }
.lerni-usage { background: #fef3c7; color: #78350f; border-radius: 8px; padding: .4rem .7rem; }
#lerni-drawer { position: fixed !important; top: 0; bottom: 0; left: 0; z-index: 1001;
  width: min(80vw, 320px); padding: 16px !important; overflow-y: auto;
  background: var(--background-fill-primary); box-shadow: 2px 0 12px rgba(0, 0, 0, .2);
  transform: translateX(-105%); transition: transform .2s ease; }
#lerni-drawer.lerni-open { transform: none; }
.lerni-backdrop { display: none; position: fixed; inset: 0; z-index: 1000;
  background: rgba(0, 0, 0, .35); }
.lerni-backdrop.lerni-open { display: block; }
.lerni-nav-item { justify-content: flex-start !important; font-size: 18px !important;
  padding: 12px !important; background: none !important; box-shadow: none !important; }
.lerni-nav-item.lerni-here { background: var(--color-accent-soft) !important;
  font-weight: 600; }
#lerni-ask-chat :is(p, li), #lerni-home-chat :is(p, li) { font-size: 19px !important;
  line-height: 1.45 !important; }
.lerni-type textarea { font-size: 18px !important; }
/* the chat fills the screen above the dock (talk.js sizes it exactly) */
#lerni-ask-chat, #lerni-home-chat { height: calc(100dvh - 330px) !important;
  min-height: 160px; }
/* the student's racing this week: a row per goal with a bar, then ⭐ and car chips */
.lerni-week h3 { margin: 4px 0 6px; }
.lerni-week-row { display: grid; grid-template-columns: minmax(0, 1fr) 72px 60px; gap: 8px;
  align-items: center; padding: 5px 0; border-bottom: 1px solid var(--border-color-primary); }
.lerni-week-row > span:first-child { overflow-wrap: anywhere; }
.lerni-week-bar { height: 8px; border-radius: 4px; background: var(--border-color-primary);
  overflow: hidden; }
.lerni-week-bar i { display: block; height: 8px; background: #1d9e75; }
.lerni-of { text-align: right; color: var(--body-text-color-subdued); font-size: 14px; }
.lerni-chip { display: inline-block; margin: 8px 6px 0 0; padding: 2px 10px; border-radius: 8px;
  background: var(--color-accent-soft); font-size: 14px; }
/* MentalMap list: full-width rows with the 🗑 at the right; fields at 16px for iPhone */
.lerni-item { flex-wrap: nowrap !important; gap: 6px !important; align-items: center; }
.lerni-item button:first-child { justify-content: flex-start; text-align: left; }
.lerni-add input, .lerni-add textarea, .lerni-detail textarea { font-size: 16px !important; }
.lerni-detail { padding-left: 12px; border-left: 3px solid #93c5fd; }
/* Games: a coming-soon placeholder, centered */
.lerni-soon { text-align: center; padding: 15vh 1rem; }
.lerni-soon div { font-size: 120px; line-height: 1; }
.lerni-soon p { font-size: 26px !important; font-weight: 700; margin-top: 1rem; }
.lerni-dock { align-items: center; gap: 8px !important; }
.lerni-dock .lerni-type { width: 100%; }
/* Talk or Type: the voice dock shows one of them, Talk until the student picks Type */
.lerni-voice:not([data-mode="type"]) .lerni-type { display: none !important; }
.lerni-voice[data-mode="type"] .lerni-talk,
.lerni-voice[data-mode="type"] [id^="lerni-preview-"] { display: none !important; }
.lerni-mode { display: flex; width: fit-content; margin: 0 auto; border-radius: 999px;
  border: 1px solid var(--border-color-primary); overflow: hidden; font-size: 16px; }
.lerni-mode button { padding: 6px 18px; background: none; }
.lerni-mode button[aria-pressed="true"] { background: var(--color-accent-soft);
  font-weight: 600; }
/* Hold to talk: a big round button for the thumb, red and pulsing while held */
.lerni-hide { display: none !important; }
/* Games: the ⭐ in the header, big answer buttons, and a track that doesn't sprawl */
.lerni-stars { min-height: 44px !important; font-size: 16px !important; flex-grow: 0 !important;
  min-width: 0 !important; white-space: nowrap; }
#lerni-earn { font-size: 16px; padding: 8px 12px !important; border-radius: 12px;
  background: var(--color-accent-soft); }
.lerni-question p { font-size: 18px; }
.lerni-choice, .lerni-go { min-height: 56px !important; font-size: 18px !important; }
/* the garage: your car big at the top, then tiles, 2 across on a phone */
#lerni-hero { text-align: center; font-size: 18px; }
.lerni-hero-car img, .lerni-hero-car svg { width: 100%; max-width: 480px; height: auto; }
.lerni-hero-name { font-size: 22px; }
.lerni-goal { margin: 8px auto 0; max-width: 480px; font-size: 16px; }
.lerni-bar { height: 12px; margin-top: 6px; border-radius: 6px;
  background: var(--border-color-primary); overflow: hidden; }
.lerni-bar span { display: block; height: 100%; background: #EF9F27; }
.lerni-tiles { display: grid !important; gap: 10px !important;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); }
.lerni-tile { border: 1px solid var(--border-color-primary); border-radius: 12px;
  padding: 8px !important; justify-content: space-between !important; }
.lerni-card { display: flex; flex-direction: column; gap: 2px; font-size: 16px; }
.lerni-card img, .lerni-card svg { width: 100%; height: auto; }
.lerni-usd { font-size: 20px; font-weight: 700; }
.lerni-like, .lerni-card details { font-size: 14px; }
.lerni-buy { min-height: 48px !important; font-size: 16px !important; }
#lerni-track svg { max-width: 820px; display: block; margin: 0 auto; }
.lerni-mute { display: block; margin: 2px 0 0 auto; min-width: 44px; min-height: 44px;
              font-size: 20px; background: none; border: none; cursor: pointer; }
/* MentalMap pictures (mapview.js): a tapped item lights up its links; the rest fades */
.lerni-map .lerni-node { cursor: pointer; }
.lerni-map svg.lerni-focus .lerni-node:not(.lerni-near) { opacity: 0.15; }
.lerni-map svg.lerni-focus line:not(.lerni-near) { opacity: 0.1; }
.lerni-map .lerni-picked circle { stroke: #222; stroke-width: 4; }
.lerni-map-reset { font-size: 13px; padding: 4px 10px; border-radius: 6px; margin-top: 4px; }
.lerni-talk { width: 120px !important; height: 120px !important; min-width: 0 !important;
  flex: none !important; border-radius: 50% !important; font-size: 17px !important;
  white-space: pre-line; line-height: 1.3; background: var(--button-primary-background-fill)
  !important; color: var(--button-primary-text-color) !important; touch-action: none;
  user-select: none; -webkit-user-select: none; -webkit-touch-callout: none; }
.lerni-listening { background: #dc2626 !important; color: white !important;
  animation: lerni-pulse 1s ease-in-out infinite; }
@keyframes lerni-pulse { 50% { transform: scale(1.06); } }
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


def _head(speech: bool) -> str:
    """The page's scripts, inlined so it loads nothing else: menu, map taps, Hold to talk."""
    from importlib.resources import files

    names = ["nav.js", "mapview.js", "race.js"] + (["talk.js"] if speech else [])
    return "".join(f"<script>{files('lerni.student.web').joinpath(n).read_text()}</script>"
                   for n in names)


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
    speech: Speech | None = None,
    usage: Usage | None = None,
    quizzer: Quizzer | None = None,
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
        speech: Speech to text and back for Hold to talk; ``None`` turns it off.
        usage: Claude usage, for the educators' warning; ``None`` shows none.
        quizzer: Claude behind an adapter for race questions; ``None`` turns races off.
    """
    root = data_root or default_data_dir()
    students = StudentStore(root)
    signin = SignIn(students, load_secret(root))
    # our own server; we turn off its docs pages too
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    add_signin_routes(app, signin, label, version)

    @app.middleware("http")
    async def on_every_request(request: Request, call_next: Any) -> Any:
        # Gradio's own limit doesn't apply when it's mounted, so uploads are checked here
        if request.url.path.endswith("/gradio_api/upload"):
            size = request.headers.get("content-length", "")
            if not size.isdigit() or int(size) > MAX_UPLOAD_REQUEST:
                return PlainTextResponse(
                    "That file is too big (the limit is 5 MB).", status_code=413
                )
        response = await call_next(request)
        if response.headers.get("content-type", "").startswith("text/html"):
            # pages are never reused after an update; Safari kept an old script otherwise
            response.headers["Cache-Control"] = "no-store"
        return response

    def current_user(request: Request) -> str | None:
        # runs on every request: no valid cookie, no access
        viewer = signin.viewer_from_cookie(request.cookies.get(cookie_name(label)))
        return viewer.username if viewer else None

    maps, log = MapStore(root), ConversationLog(root)
    points, garage = PointsStore(root), Garage(root)

    @app.get("/cars/{car_id}")
    def car_picture(car_id: str, request: Request) -> Any:
        # a picture only for someone signed in, and only for a car in the garage
        if current_user(request) is None:
            return RedirectResponse("/signin", status_code=303)
        path = garage.picture(car_id)
        if path is None or not path.is_file():
            return PlainTextResponse("Not found.", status_code=404)
        return FileResponse(path, headers={"Cache-Control": "private, max-age=86400"})

    @app.get("/sounds/{name}")
    def race_sound(name: str, request: Request) -> Any:
        # the admin's own clips, kept out of the repo: only the race's names, only signed in
        if current_user(request) is None:
            return RedirectResponse("/signin", status_code=303)
        path = root / "sounds" / f"{name}.mp3"
        if name not in SOUNDS or not path.is_file():
            return PlainTextResponse("Not found.", status_code=404)
        return FileResponse(path, media_type="audio/mpeg",  # revalidated, so a swapped clip plays
                            headers={"Cache-Control": "private, no-cache"})

    races = (RaceDesk(quizzer, maps, points, ConceptStore(root), results=ResultsLog(root),
                      checker=quizzer,  # the same small model answers each question blind
                      garage=garage, grader=quizzer,  # and grades bonus answers
                      log=log)  # a worrying bonus answer is kept where Chat's are
             if quizzer is not None else None)
    log.purge()  # at startup; then once a day as exchanges are logged
    # production only (a labelled server is development): a restart loses held questions
    if races is not None and not label:
        for s in students.list_students():
            if s.kind is Kind.SUPERVISED and not s.archived:
                try:  # best effort: the next race's questions, in the background
                    races.prefill(s.username, supervised=True)
                except Exception:  # noqa: BLE001 - a broken file never stops the server
                    pass

    def plays(username: str) -> bool:  # supervised students and educators earn ⭐
        try:
            student = students.get(username)
        except AccountError:
            return False
        return student.kind is Kind.SUPERVISED or student.educator

    keeper = MapKeeper(maps, tagger, log, points=points, earns=plays)
    conversations = (
        Conversations(
            chat_model, context=keeper.context, on_exchange=keeper.after, spoken=speech is not None
        )
        if chat_model
        else None
    )
    view = build_main_view(
        signin,
        students,
        maps,
        conversations,
        uploader=uploader,
        feedback=FeedbackStore(root),
        label=label,
        speech=speech,
        educator_chats=EducatorChats(chat_model, maps, log) if chat_model else None,
        usage=usage,
        points=points,
        races=races,
        garage=garage,
    )
    mounted = gr.mount_gradio_app(
        app,
        view,
        path=APP_PATH,
        auth_dependency=current_user,
        theme=_theme(),
        css=_CSS,
        head=_head(speech is not None),
        **_MOUNT_OPTIONS,
    )
    # Gradio refuses file paths outside its upload folder only once launched; mounted apps never are
    view.has_launched = True
    return mounted
