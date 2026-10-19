"""LaunchAgents: the property list for a server, and launchctl called in order."""

import plistlib

from lerni.student.service import Server, install


def test_install_writes_the_agent_and_replaces_any_old_one(tmp_path):
    calls = []

    def run(args, **kwargs):  # a fake launchctl: records, never runs
        calls.append(args)

        class Done:
            returncode = 3 if args[1] == "bootout" else 0  # "not loaded" on a first install

        return Done()

    dev = Server("dev", 7861, "Development", tmp_path / "dev-data",
                 tmp_path / "https.pem", tmp_path / "https-key.pem")
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
