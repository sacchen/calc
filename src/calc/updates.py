from __future__ import annotations

import json
import re
from urllib.request import urlopen

_SEMVERISH_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:\.dev(\d+))?$")


def latest_pypi_version(package_name: str, *, urlopen_fn=urlopen) -> str | None:
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        with urlopen_fn(url, timeout=2.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload.get("info", {}).get("version")
    except (OSError, TimeoutError, ValueError):
        return None


def compare_versions(current: str, latest: str) -> int | None:
    current_match = _SEMVERISH_PATTERN.match(current)
    latest_match = _SEMVERISH_PATTERN.match(latest)
    if current_match is None or latest_match is None:
        return None

    current_release = tuple(int(part) for part in current_match.group(1, 2, 3))
    latest_release = tuple(int(part) for part in latest_match.group(1, 2, 3))
    if current_release < latest_release:
        return -1
    if current_release > latest_release:
        return 1

    current_dev = current_match.group(4)
    latest_dev = latest_match.group(4)
    if current_dev is None and latest_dev is None:
        return 0
    if current_dev is None:
        return 1
    if latest_dev is None:
        return -1

    current_dev_num = int(current_dev)
    latest_dev_num = int(latest_dev)
    if current_dev_num < latest_dev_num:
        return -1
    if current_dev_num > latest_dev_num:
        return 1
    return 0


def update_status_lines(
    version: str,
    latest: str | None,
    update_cmd: str,
    *,
    compare_fn=compare_versions,
) -> list[str]:
    if version == "dev":
        return [
            "current version: dev (local checkout)",
            "latest version: unknown from local checkout",
            "install latest local changes with: uv tool install --force --reinstall --refresh .",
        ]

    lines = [f"current version: {version}"]
    if latest is None:
        lines.append("latest version: unavailable (offline or PyPI unreachable)")
        lines.append("hint: retry :check when online")
        return lines

    relation = compare_fn(version, latest)
    if relation == 0 or latest == version:
        lines.append(f"latest version: {latest} (up to date)")
        lines.append("no update needed")
    elif relation == -1:
        lines.append(f"latest version: {latest} (update available)")
        lines.append(f"update with: {update_cmd}")
    elif relation == 1:
        lines.append(f"latest version: {latest} (you are on a newer local/pre-release build)")
        lines.append("no update needed")
    else:
        lines.append(f"latest version: {latest} (version comparison unavailable)")
        lines.append(f"update with: {update_cmd}")
    return lines


def repl_startup_update_status_lines(
    version: str,
    latest: str | None,
    update_cmd: str,
    *,
    compare_fn=compare_versions,
) -> list[str]:
    if version == "dev":
        return ["startup update check: dev (local checkout)"]
    if latest is None:
        return ["startup update check: latest version unavailable"]

    relation = compare_fn(version, latest)
    if relation == 0 or latest == version:
        return [f"startup update check: v{version} is up to date"]
    if relation == -1:
        return [
            f"startup update check: v{latest} available (you have v{version})",
            f"update with: {update_cmd}",
        ]
    if relation == 1:
        return [f"startup update check: v{version} is newer than latest release v{latest}"]
    return ["startup update check: version comparison unavailable"]
