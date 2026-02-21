import calc.updates as updates


class _DummyResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._payload


def test_latest_pypi_version_success():
    def fake_urlopen(url: str, timeout: float):
        assert "pypi.org/pypi/philcalc/json" in url
        assert timeout == 2.0
        return _DummyResponse(b'{"info":{"version":"1.2.3"}}')

    assert updates.latest_pypi_version("philcalc", urlopen_fn=fake_urlopen) == "1.2.3"


def test_latest_pypi_version_failures():
    def os_error(*args, **kwargs):
        raise OSError("offline")

    assert updates.latest_pypi_version("philcalc", urlopen_fn=os_error) is None

    def bad_json(*args, **kwargs):
        return _DummyResponse(b"{")

    assert updates.latest_pypi_version("philcalc", urlopen_fn=bad_json) is None


def test_compare_versions_all_branches():
    assert updates.compare_versions("1.2.3", "1.2.3") == 0
    assert updates.compare_versions("1.2.3", "1.2.4") == -1
    assert updates.compare_versions("1.2.4", "1.2.3") == 1
    assert updates.compare_versions("1.2.3", "1.2.3.dev1") == 1
    assert updates.compare_versions("1.2.3.dev1", "1.2.3") == -1
    assert updates.compare_versions("1.2.3.dev1", "1.2.3.dev2") == -1
    assert updates.compare_versions("1.2.3.dev3", "1.2.3.dev2") == 1
    assert updates.compare_versions("1.2.3.dev2", "1.2.3.dev2") == 0
    assert updates.compare_versions("wat", "1.2.3") is None


def test_update_status_lines_branches():
    cmd = "uv tool upgrade philcalc"
    assert updates.update_status_lines("dev", None, cmd)[0] == "current version: dev (local checkout)"

    unavailable = updates.update_status_lines("1.2.3", None, cmd)
    assert "latest version: unavailable" in unavailable[1]

    up_to_date = updates.update_status_lines("1.2.3", "1.2.3", cmd)
    assert "up to date" in up_to_date[1]
    assert "no update needed" in up_to_date[2]

    update_available = updates.update_status_lines("1.2.3", "1.2.4", cmd)
    assert "update available" in update_available[1]
    assert update_available[2] == f"update with: {cmd}"

    newer_local = updates.update_status_lines("1.2.3.dev1", "1.2.2", cmd)
    assert "newer local/pre-release build" in newer_local[1]

    unknown_compare = updates.update_status_lines(
        "1.2.3",
        "1.2.4",
        cmd,
        compare_fn=lambda a, b: None,
    )
    assert "version comparison unavailable" in unknown_compare[1]
    assert unknown_compare[2] == f"update with: {cmd}"


def test_repl_startup_update_status_lines_branches():
    cmd = "uv tool upgrade philcalc"
    assert updates.repl_startup_update_status_lines("dev", "1.2.3", cmd) == [
        "startup update check: dev (local checkout)"
    ]
    assert updates.repl_startup_update_status_lines("1.2.3", None, cmd) == [
        "startup update check: latest version unavailable"
    ]
    assert updates.repl_startup_update_status_lines("1.2.3", "1.2.3", cmd) == [
        "startup update check: v1.2.3 is up to date"
    ]
    assert updates.repl_startup_update_status_lines("1.2.3", "1.2.4", cmd) == [
        "startup update check: v1.2.4 available (you have v1.2.3)",
        f"update with: {cmd}",
    ]
    assert updates.repl_startup_update_status_lines("1.2.4", "1.2.3", cmd) == [
        "startup update check: v1.2.4 is newer than latest release v1.2.3"
    ]
    assert updates.repl_startup_update_status_lines(
        "1.2.3",
        "1.2.4",
        cmd,
        compare_fn=lambda a, b: None,
    ) == ["startup update check: version comparison unavailable"]
