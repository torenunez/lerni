"""The sign-in page: a plain HTML form Safari and Keychain can save.

It posts normally (no script), sets the signed ``lerni_session`` cookie, and
sends the browser to the app. Signed-out visits to the app come here.
"""

from __future__ import annotations

from html import escape

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from lerni.student.signin import COOKIE_NAME, SESSION_SECONDS, SignIn

APP_PATH = "/app"

# System fonts and inline CSS only, so the iPad loads nothing from outside.
_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lerni: sign in</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif; margin: 0; min-height: 100vh;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #ffe17a 0%, #ff9fb2 45%, #8fd3ff 100%); color: #1b1340; }}
form {{ background: rgba(255,255,255,.85); padding: 2rem; border-radius: 24px;
  width: min(90vw, 360px); display: flex; flex-direction: column; gap: .8rem; }}
h1 {{ margin: 0 0 .5rem; font-size: 2.2rem; }}
label {{ font-weight: 600; }}
input {{ font-size: 1.3rem; padding: .6rem; border-radius: 12px; border: 1px solid #999; }}
button {{ font-size: 1.3rem; padding: .7rem; border-radius: 999px; border: 0;
  background: #1b1340; color: white; font-weight: 700; }}
.error {{ color: #a10000; }}
.version {{ position: fixed; bottom: .4rem; left: 0; right: 0; text-align: center;
  font-size: .75rem; color: #555; }}
.env {{ position: fixed; top: 0; left: 0; right: 0; padding: .3rem; text-align: center;
  background: #6b21a8; color: white; font-weight: 700; }}
</style></head><body>
{label}<form method="post" action="/signin">
  <h1>👋 Lerni</h1>
  <p class="error" role="alert">{message}</p>
  <label for="username">Username</label>
  <input id="username" name="username" autocomplete="username" autocapitalize="none"
    autocorrect="off" spellcheck="false" required>
  <label for="password">Password</label>
  <input id="password" name="password" type="password" autocomplete="current-password" required>
  <button type="submit">Sign in</button>
  <p>{hint}</p>
</form>{version}</body></html>"""


NO_ACCOUNTS_HINT = (
    "No accounts yet. On the home server, run: lerni student add USERNAME "
    "--name NAME --kind independent --educator"
)


def _page(
    message: str = "", status: int = 200, first_start: bool = False, label: str = "",
    version: str = "",
) -> HTMLResponse:
    hint = NO_ACCOUNTS_HINT if first_start else "No account yet? Ask your educator."
    # a development server says so; production has no label
    strip = f'<div class="env">{escape(label)}</div>' if label else ""
    return HTMLResponse(
        _PAGE.format(message=escape(message), hint=escape(hint), label=strip,
                     version=f'<p class="version">{escape(version)}</p>' if version else ""),
        status_code=status,
    )


def add_signin_routes(
    app: FastAPI, signin: SignIn, label: str = "", version: str = ""
) -> None:
    """Add ``/``, ``/signin``, ``/signout``, and the signed-out redirect for the app page."""

    @app.middleware("http")
    async def signed_out_to_signin(request: Request, call_next):  # type: ignore[no-untyped-def]
        # only the app's page itself redirects; its API calls get Gradio's 401
        if request.method == "GET" and request.url.path in (APP_PATH, APP_PATH + "/"):
            if signin.viewer_from_cookie(request.cookies.get(COOKIE_NAME)) is None:
                return RedirectResponse("/signin", status_code=303)
        return await call_next(request)

    @app.get("/")
    def root(request: Request) -> Response:
        signed_in = signin.viewer_from_cookie(request.cookies.get(COOKIE_NAME))
        return RedirectResponse(APP_PATH + "/" if signed_in else "/signin", status_code=303)

    @app.get("/signin")
    def signin_form() -> HTMLResponse:
        return _page(first_start=not signin.students.list_students(), label=label, version=version)

    @app.post("/signin")
    def signin_submit(username: str = Form(""), password: str = Form("")) -> Response:
        cookie, message = signin.attempt(username, password)
        if cookie is None:
            return _page(message, status=401, label=label, version=version)
        response = RedirectResponse(APP_PATH + "/", status_code=303)
        response.set_cookie(
            COOKIE_NAME, cookie, max_age=SESSION_SECONDS, httponly=True, samesite="lax", path="/"
        )
        return response

    @app.get("/signout")
    def signout() -> Response:
        # this device only; other devices stay signed in
        response = RedirectResponse("/signin", status_code=303)
        response.delete_cookie(COOKIE_NAME, path="/")
        return response
