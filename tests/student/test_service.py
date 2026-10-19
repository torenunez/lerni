"""LaunchAgents: the property list for a server, and launchctl called in order."""

import plistlib
import subprocess

import pytest

from lerni.student.service import Server, ServiceError, install, restart, status


def test_install_writes_the_agent_and_replaces_any_old_one(tmp_path):
    calls = []

    def run(args, **kwargs):  # a fake launchctl: records, never runs
        calls.append(args)

        class Done:
            returncode = 3 if args[1] == "bootout" else 0  # "not loaded" on a first install

        return Done()

    dev = Server("dev", 7861, "Development", tmp_path / "dev-data",
                 tmp_path / "https.pem", tmp_path / "https-key.pem")
    (tmp_path / "venv/bin").mkdir(parents=True)
    (tmp_path / "venv/bin/lerni").write_text("")
    path = install(dev, run=run, home=tmp_path, lerni=tmp_path / "venv/bin/lerni",
                   checkout=tmp_path / "checkout", path_env="/opt/homebrew/bin:/usr/bin", uid=501)
    agent = plistlib.loads(path.read_bytes())
    assert path == tmp_path / "Library/LaunchAgents/com.lerni.dev.plist"
    assert agent["ProgramArguments"] == [
        str(tmp_path / "venv/bin/lerni"), "serve", "--port", "7861", "--label", "Development",
        "--cert", str(tmp_path / "https.pem"), "--key", str(tmp_path / "https-key.pem")]
    assert agent["EnvironmentVariables"] == {"PATH": "/opt/homebrew/bin:/usr/bin",
                                             "LERNI_STUDENT_DATA": str(tmp_path / "dev-data")}
    assert agent["WorkingDirectory"] == str(tmp_path / "checkout")
    assert agent["KeepAlive"] and agent["RunAtLoad"] and agent["LimitLoadToSessionType"] == "Aqua"
    assert agent["StandardOutPath"] == str(tmp_path / "Library/Logs/lerni/dev.log")
    assert calls == [["launchctl", "bootout", "gui/501/com.lerni.dev"],
                     ["launchctl", "bootstrap", "gui/501", str(path)]]


class Launchctl:
    """A fake launchctl that answers each command from a script of results."""

    def __init__(self, **results):
        self.results, self.calls = results, []

    def __call__(self, args, check=False, **kwargs):
        self.calls.append(args)
        code, out = self.results.get(args[1], [(0, "")]).pop(0) if self.results.get(args[1]) \
            else (0, "")
        if check and code:
            raise subprocess.CalledProcessError(code, args)
        return subprocess.CompletedProcess(args, code, stdout=out)


def test_install_and_restart_fail_plainly_and_dev_never_uses_production_data(tmp_path):
    lerni = tmp_path / "lerni"
    lerni.write_text("")
    cert, key = tmp_path / "c.pem", tmp_path / "k.pem"
    # regression: dev without --data ran on the real maps and logs
    with pytest.raises(ServiceError):
        install(Server("dev", 7861, "Development", None, cert, key), run=Launchctl(),
                home=tmp_path, lerni=lerni, uid=501)
    # regression: a wrong program path crash-looped silently
    with pytest.raises(ServiceError):
        install(Server("prod", 7860, "", None, cert, key), run=Launchctl(), home=tmp_path,
                lerni=tmp_path / "nowhere", uid=501)
    # regression: bootstrap right after bootout can fail once ("Input/output error")
    flaky = Launchctl(bootstrap=[(5, ""), (0, "")])
    install(Server("prod", 7860, "", None, cert, key), run=flaky, home=tmp_path, lerni=lerni,
            uid=501, wait=0)
    assert [c[1] for c in flaky.calls] == ["bootout", "bootstrap", "bootstrap"]
    # regression: restart before install gave a traceback
    with pytest.raises(ServiceError, match="install"):
        restart("dev", run=Launchctl(kickstart=[(113, "")]), uid=501)


def test_status_is_not_fooled_by_another_copy_on_the_port(tmp_path, monkeypatch):
    # regression: a Terminal copy answered while the agent crash-looped, and status said healthy
    import lerni.student.service as service

    lerni = tmp_path / "lerni"
    lerni.write_text("")
    install(Server("prod", 7860, "", None, tmp_path / "c.pem", tmp_path / "k.pem"),
            run=Launchctl(), home=tmp_path, lerni=lerni, uid=501)
    monkeypatch.setattr(service, "_answers", lambda port: True)
    shown = Launchctl(print=[(0, "\tpid = 10\n")])
    monkeypatch.setattr(service, "_listener", lambda port: 99)  # someone else holds the port
    assert "not answering" in status("prod", run=shown, uid=501, home=tmp_path)
    monkeypatch.setattr(service, "_listener", lambda port: 10)
    shown = Launchctl(print=[(0, "\tpid = 10\n")])
    assert "running (pid 10)" in status("prod", run=shown, uid=501, home=tmp_path)
