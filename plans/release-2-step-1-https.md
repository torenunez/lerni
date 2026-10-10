# Release 2, step 1: HTTPS — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `lerni serve --cert … --key …` serves the student app over HTTPS with a certificate the admin makes with mkcert and installs once on each device, so iPad Safari will allow the microphone in step 2.

**Architecture:** uvicorn's own TLS (`ssl_certfile`, `ssl_keyfile`); the sign-in cookie gets `Secure` when the request came over HTTPS; the admin reference gains the mkcert setup. No new dependency.

**Tech Stack:** uvicorn, FastAPI, typer; mkcert (the admin installs it with Homebrew on the home server; not a Python dependency).

**Spec:** [plans/specs/05-voice.md](specs/05-voice.md) ("Decisions": HTTPS; "Build order" R2-1).

## Global Constraints

- HTTPS only when both `--cert` and `--key` are given; one without the other, or a file that doesn't exist, is refused with a short message before the server starts. Without them, plain HTTP as today.
- The sign-in cookie: `HttpOnly`, `SameSite=Lax`, 30 days, and `Secure` when the request came over HTTPS.
- Home network only; no certificate or key in the repo, ever (they live in the admin's home folder; the private-words check refuses `secret.key`, and the admin reference says where the files go).
- Tests use fakes, no network, minimal. Comment code concisely. Line length 100. Manifest rows for changed files' descriptions.

## Review Focus

- **Only one of `--cert`/`--key`, or a missing file:** a clear message, not a uvicorn traceback. (Task 2 test.)
- **Sign-in over HTTPS:** the cookie is `Secure`; over HTTP it isn't (or no device could sign in before HTTPS is set up). (Task 1 test.)
- **The startup line** names `https://` when serving HTTPS. (Task 2 test.)

---

### Task 1: The cookie is `Secure` over HTTPS

**Files:** Modify `src/lerni/student/web/signin_page.py` (`signin_submit`); Test `tests/student/test_web_signin.py`.

- [ ] **Step 1: Write the failing test** (append; reuse the module's account setup, read its top first)

```python
def test_the_cookie_is_secure_only_over_https(tmp_path):
    StudentStore(tmp_path).add("sam", "Sam", Kind.INDEPENDENT, "long enough")
    for base, secure in (("https://lerni.test", True), ("http://lerni.test", False)):
        client = TestClient(build_app(data_root=tmp_path), base_url=base, follow_redirects=False)
        response = client.post("/signin", data={"username": "sam", "password": "long enough"})
        assert ("secure" in response.headers["set-cookie"].lower()) is secure
```

- [ ] **Step 2: Run it**

Run: `.venv/bin/python -m pytest -q tests/student/test_web_signin.py -k secure`
Expected: FAIL on the HTTPS case.

- [ ] **Step 3: Implement**

```python
    @app.post("/signin")
    def signin_submit(
        request: Request, username: str = Form(""), password: str = Form("")
    ) -> Response:
        cookie, message = signin.attempt(username, password)
        if cookie is None:
            return _page(message, status=401)
        response = RedirectResponse(APP_PATH + "/", status_code=303)
        response.set_cookie(
            COOKIE_NAME, cookie, max_age=SESSION_SECONDS, httponly=True, samesite="lax",
            path="/", secure=request.url.scheme == "https",  # Secure once served over HTTPS
        )
        return response
```

- [ ] **Step 4: Run tests and commit**

Run: `.venv/bin/python -m pytest -q && .venv/bin/python -m ruff check src/lerni/student/web/signin_page.py tests/student/test_web_signin.py`
Expected: all pass; ruff clean.

Manifest: `signin_page.py` row adds "the cookie is `Secure` over HTTPS"; `test_web_signin.py` row adds the same.

```bash
git add src/lerni/student/web/signin_page.py tests/student/test_web_signin.py docs/code-manifest.md
git commit -m "Sign-in cookie: Secure over HTTPS"
```

---

### Task 2: `lerni serve --cert --key`

**Files:** Modify `src/lerni/student/web/serve.py` (`serve`), `src/lerni/commands/serve.py` (`serve_cmd`); Test `tests/student/test_serve.py`.

**Interfaces:** `serve(host: str, port: int, cert: Path | None = None, key: Path | None = None) -> None`; raises `ValueError` with a short message for one file without the other, or a missing file.

- [ ] **Step 1: Write the failing test** (append)

```python
def test_https_needs_both_files_and_passes_them_to_uvicorn(monkeypatch, tmp_path, capsys):
    import uvicorn

    from lerni.student.web import serve

    seen = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: seen.update(kwargs))
    for name in ("_claude_tagger", "_claude_uploader", "_claude_chat"):
        monkeypatch.setattr(serve, name, lambda: None)
    cert, key = tmp_path / "home.pem", tmp_path / "home-key.pem"
    with pytest.raises(ValueError):
        serve.serve("127.0.0.1", 0, cert=cert)  # a key is needed too
    with pytest.raises(ValueError):
        serve.serve("127.0.0.1", 0, cert=cert, key=key)  # files that don't exist
    cert.write_text("cert")
    key.write_text("key")
    serve.serve("127.0.0.1", 0, cert=cert, key=key)
    assert seen["ssl_certfile"] == str(cert) and seen["ssl_keyfile"] == str(key)
    assert "https://" in capsys.readouterr().out
```

- [ ] **Step 2: Run it**

Run: `.venv/bin/python -m pytest -q tests/student/test_serve.py`
Expected: FAIL (`serve()` takes no `cert`).

- [ ] **Step 3: Implement**

In `web/serve.py` (add `from pathlib import Path`):

```python
def serve(host: str, port: int, cert: Path | None = None, key: Path | None = None) -> None:
    """Start the student app and block until it stops.

    Args:
        host: Address to bind. ``0.0.0.0`` lets devices on the home network reach it.
        port: Port to listen on.
        cert: The HTTPS certificate (from mkcert); with ``key``, serves HTTPS.
        key: The certificate's private key.

    Raises:
        ValueError: Only one of ``cert`` and ``key``, or a file that doesn't exist.
    """
    if (cert is None) != (key is None):
        raise ValueError("HTTPS needs both --cert and --key.")
    for path in (cert, key):
        if path is not None and not path.is_file():
            raise ValueError(f"No such file: {path}")
    scheme = "https" if cert else "http"
```

Then: the startup line `print(f"Sign in:  {scheme}://<this-computer>:{port}/", flush=True)`, and pass `ssl_certfile=str(cert) if cert else None, ssl_keyfile=str(key) if key else None` to `uvicorn.run`.

In `commands/serve.py` add the options and turn `ValueError` into a red message and exit 1:

```python
    cert: Path = typer.Option(None, help="HTTPS certificate (from mkcert); needs --key."),
    key: Path = typer.Option(None, help="The certificate's private key; needs --cert."),
...
    try:
        serve(host=host, port=port, cert=cert, key=key)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from None
```

- [ ] **Step 4: Run tests and commit**

Run: `.venv/bin/python -m pytest -q && .venv/bin/python -m ruff check src/lerni/student/web/serve.py src/lerni/commands/serve.py tests/student/test_serve.py`
Expected: all pass; ruff clean.

Manifest: `web/serve.py` and `commands/serve.py` rows mention `--cert`/`--key` (HTTPS); `test_serve.py` row adds "HTTPS needs both files".

```bash
git add src/lerni/student/web/serve.py src/lerni/commands/serve.py tests/student/test_serve.py docs/code-manifest.md
git commit -m "lerni serve --cert --key: HTTPS on the home server"
```

---

### Task 3: Setup docs

**Files:** Modify `docs/reference/admin.md` (it says `<home-server>`; the real name stays in the gitignored `CLAUDE.local.md`), `docs/ARCHITECTURE.md`, `docs/prd/admin.md` (answer the HTTPS open question), `docs/todo.md`, `docs/progress.md`, `docs/roadmap.md`.

- [ ] **Step 1: Admin reference — "HTTPS on the home server"** (under "Running the student app"):

```markdown
### HTTPS (for voice)

iPad Safari allows the microphone only over HTTPS. Lerni uses its own certificate, made once with [mkcert](https://github.com/FiloSottile/mkcert) on the home server:

1. `brew install mkcert`, then `mkcert -install` (creates a small private certificate authority on this Mac).
2. Make the server's certificate, naming every way devices reach it: `mkcert -cert-file ~/.lerni/student/https.pem -key-file ~/.lerni/student/https-key.pem <home-server>.local <its-IP> localhost`. The key stays on the home server; never copy it into the repo.
3. On each device (iPad, phones): send it the authority's certificate, `"$(mkcert -CAROOT)/rootCA.pem"` (AirDrop works), open it to install the profile (Settings → Profile Downloaded → Install), then turn on full trust (Settings → General → About → Certificate Trust Settings).
4. Start with `lerni serve --cert ~/.lerni/student/https.pem --key ~/.lerni/student/https-key.pem` and open `https://<home-server>.local:7860/`.

Safari's saved password is for the old `http://` address; sign in once more and let it save again. If the server's IP changes, make the certificate again (step 2).
```

- [ ] **Step 2: Other docs**

- `docs/ARCHITECTURE.md`: "Release 2 (voice) adds HTTPS" → "HTTPS is on when `lerni serve` gets `--cert` and `--key` (mkcert; Release 2)".
- `docs/prd/admin.md`: the "[NEEDS CLARIFICATION] (Release 2) How to add HTTPS…" open question becomes a dated decision: "2026-10-10: HTTPS on the home server uses a locally trusted certificate from mkcert, installed once on each device; no outside account."
- `docs/roadmap.md`: Release 2 status "In progress: step 1 (HTTPS)".
- `docs/todo.md`: under Release 2, the "how the iPad will trust its HTTPS certificate" part is done; add an Admin task: "Set up HTTPS on the home server (admin reference: HTTPS) and install the certificate on the iPad and phones."
- `docs/progress.md`: a log entry headed with the build date.

- [ ] **Step 3: Run the gate and commit**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass.

```bash
git add docs
git commit -m "Docs: HTTPS on the home server"
```

---

## Done when (from the spec)

The iPad opens the app over HTTPS with no warning, and signing in works (the admin, on the real devices).
