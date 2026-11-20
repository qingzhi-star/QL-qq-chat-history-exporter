"""由用户显式触发的公开发行版本检查。"""
from __future__ import annotations

from dataclasses import dataclass
import http.client
import json
import re
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from qqexport.errors import UserError


_REPOSITORY = "qingzhi-star/QL-qq-chat-history-exporter"
_RELEASES = f"https://github.com/{_REPOSITORY}/releases"
_API = f"https://api.github.com/repos/{_REPOSITORY}/releases?per_page=30"
_VERSION = re.compile(r"(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})(?:rc([1-9][0-9]{0,5}))?")
_MAX_RESPONSE = 4 * 1024 * 1024
_MAX_NOTES = 12_000


class UpdateError(UserError):
    pass


@dataclass(frozen=True)
class Release:
    version: str
    notes: str

    @property
    def url(self) -> str:
        return f"{_RELEASES}/tag/v{self.version}"


@dataclass(frozen=True)
class UpdateStatus:
    current: str
    status: str
    release: Release | None = None


def _version_key(value: str) -> tuple[int, int, int, bool, int]:
    match = _VERSION.fullmatch(value)
    if match is None:
        raise UpdateError("版本号格式不受支持")
    major, minor, patch, candidate = match.groups()
    return int(major), int(minor), int(patch), candidate is None, int(candidate or 0)


def _has_package_identity() -> bool:
    if sys.platform != "win32":
        return False

    import ctypes
    from ctypes import wintypes

    get_package = ctypes.WinDLL("kernel32").GetCurrentPackageFullName
    get_package.argtypes = [ctypes.POINTER(wintypes.UINT), wintypes.LPWSTR]
    get_package.restype = wintypes.LONG
    length = wintypes.UINT(0)
    status = get_package(ctypes.byref(length), None)
    if status == 122:  # ERROR_INSUFFICIENT_BUFFER
        return True
    if status == 15700:  # APPMODEL_ERROR_NO_PACKAGE
        return False
    raise UpdateError("无法识别安装渠道，请从原下载渠道检查更新")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _read_releases() -> list:
    request = Request(_API, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "Qilu-Update-Check",
        "X-GitHub-Api-Version": "2026-03-10",
    })
    try:
        with build_opener(_NoRedirect()).open(request, timeout=5) as response:
            body = response.read(_MAX_RESPONSE + 1)
    except HTTPError as error:
        limited = error.code == 429 or (error.code == 403 and (
            error.headers.get("X-RateLimit-Remaining") == "0" or "Retry-After" in error.headers))
        error.close()
        if limited:
            raise UpdateError("GitHub 暂时限制了检查频率，请稍后再试") from None
        raise UpdateError(f"GitHub 更新服务返回 HTTP {error.code}，请稍后重试") from None
    except (OSError, http.client.HTTPException) as error:
        if isinstance(error, TimeoutError) or (isinstance(error, URLError) and isinstance(error.reason, TimeoutError)):
            raise UpdateError("检查更新超时，请稍后重试") from None
        raise UpdateError("无法连接 GitHub，请检查网络后重试") from None

    if len(body) > _MAX_RESPONSE:
        raise UpdateError("GitHub 发行信息超过允许大小")
    try:
        releases = json.loads(body)
    except (ValueError, RecursionError):
        raise UpdateError("GitHub 返回的发行信息无法读取") from None
    if not isinstance(releases, list):
        raise UpdateError("GitHub 返回的发行信息格式无效")
    return releases


class UpdateChecker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cached: list | str = []
        self._until = 0.0

    def check(self, current: str) -> UpdateStatus:
        current_key = _version_key(current)
        if getattr(sys, "frozen", False) and _has_package_identity():
            return UpdateStatus(current, "store")

        with self._lock:
            if time.monotonic() >= self._until:
                try:
                    self._cached = _read_releases()
                except UpdateError as error:
                    self._cached = str(error)
                    self._until = time.monotonic() + 8
                else:
                    self._until = time.monotonic() + 60
            releases = self._cached
        if isinstance(releases, str):
            raise UpdateError(releases)

        selected_key = None
        selected = None
        for entry in releases:
            if not isinstance(entry, dict) or entry.get("draft") is not False:
                continue
            tag = entry.get("tag_name")
            if not isinstance(tag, str) or not tag.startswith("v"):
                continue
            version = tag[1:]
            try:
                key = _version_key(version)
            except UpdateError:
                continue
            candidate = not key[3]
            if entry.get("prerelease") is not candidate or (current_key[3] and candidate):
                continue
            if selected_key is None or key > selected_key:
                selected_key, selected = key, entry
        if selected is None:
            raise UpdateError("GitHub 暂无当前更新渠道可用的发行版本")

        notes = selected.get("body")
        if isinstance(notes, str):
            notes = notes[:_MAX_NOTES].replace("\r\n", "\n").replace("\r", "\n")
            notes = "".join(char for char in notes if char.isprintable() or char in "\n\t").strip()
        else:
            notes = ""
        release = Release(selected["tag_name"][1:], notes)
        status = "available" if selected_key > current_key else "ahead" if selected_key < current_key else "current"
        return UpdateStatus(current, status, release)


def print_update_status(current: str) -> bool:
    try:
        result = UpdateChecker().check(current)
    except UpdateError as error:
        print(f"检查更新失败：{error}", file=sys.stderr)
        return False

    if result.release is None:
        print(f"当前版本 v{current}。请在 Microsoft Store 的库中检查更新。")
        return True

    release = result.release
    if result.status == "available":
        print(f"当前版本 v{current}，发现新版本 v{release.version}。")
        if release.notes:
            print(release.notes)
        print(release.url)
    elif result.status == "ahead":
        print(f"当前版本 v{current} 高于渠道版本 v{release.version}。")
    else:
        print(f"当前已是该渠道的最新版本 v{current}。")
    return True
