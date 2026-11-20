from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json
from urllib.error import HTTPError, URLError

import pytest

from qqexport import cli, updates


def release(version, *, prerelease=False, draft=False, body="更新说明"):
    return dict(tag_name=f"v{version}", prerelease=prerelease, draft=draft, body=body,
                html_url="https://untrusted.example/ignored")


@pytest.fixture(autouse=True)
def outside_store(monkeypatch):
    monkeypatch.setattr(updates, "_has_package_identity", lambda: False)


def test_candidate_versions_sort_numerically_and_stable_wins(monkeypatch):
    entries = [release("0.5.0rc10", prerelease=True), release("0.5.0rc2", prerelease=True),
               release("0.5.0"), release("0.9.0", draft=True)]
    monkeypatch.setattr(updates, "_read_releases", lambda: entries)
    assert updates.UpdateChecker().check("0.5.0rc2").release.version == "0.5.0"
    entries.pop(2)
    result = updates.UpdateChecker().check("0.5.0rc2")
    assert result.status == "available" and result.release.version == "0.5.0rc10"
    assert result.release.url.endswith("/QL-qq-chat-history-exporter/releases/tag/v0.5.0rc10")


def test_stable_channel_and_local_version_ahead(monkeypatch):
    entries = [release("0.5.0rc10", prerelease=True), release("0.4.0"),
               release("0.4.9rc1"), release("99.0.0", prerelease=True), None]
    monkeypatch.setattr(updates, "_read_releases", lambda: entries)
    checker = updates.UpdateChecker()
    assert checker.check("0.4.0").status == "current"
    assert checker.check("0.4.1").status == "ahead"


def test_packaged_channel_never_contacts_github(monkeypatch):
    monkeypatch.setattr(updates.sys, "frozen", True, raising=False)
    monkeypatch.setattr(updates, "_has_package_identity", lambda: True)
    monkeypatch.setattr(updates, "_read_releases", lambda: pytest.fail("unexpected GitHub access"))
    assert updates.UpdateChecker().check("0.4.0").status == "store"


def test_parallel_checks_reuse_one_response(monkeypatch):
    requests = []

    def read():
        requests.append(True)
        return [release("0.4.0")]

    monkeypatch.setattr(updates, "_read_releases", read)
    checker = updates.UpdateChecker()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(checker.check, ["0.4.0"] * 8))
    assert len(requests) == 1 and all(item.status == "current" for item in results)


@pytest.mark.parametrize(("error", "message"), [
    (URLError(OSError("offline")), "无法连接"),
    (URLError(TimeoutError()), "超时"),
    (HTTPError("https://api.github.com", 403, "limit", {"X-RateLimit-Remaining": "0"}, None), "限制"),
    (HTTPError("https://api.github.com", 500, "server", {}, None), "HTTP 500"),
])
def test_network_errors_are_actionable(monkeypatch, error, message):
    class Opener:
        def open(self, request, timeout):
            raise error

    monkeypatch.setattr(updates, "build_opener", lambda *handlers: Opener())
    with pytest.raises(updates.UpdateError, match=message):
        updates.UpdateChecker().check("0.4.0")


def test_bad_responses_and_bounded_release_body(monkeypatch):
    class Opener:
        body = b"{unknown"

        def open(self, request, timeout):
            assert request.full_url == updates._API and timeout == 5
            assert not request.has_header("Authorization")
            return BytesIO(self.body)

    opener = Opener()
    monkeypatch.setattr(updates, "build_opener", lambda *handlers: opener)
    for body in (b"{unknown", b"{}", b"x" * (updates._MAX_RESPONSE + 1)):
        opener.body = body
        with pytest.raises(updates.UpdateError):
            updates.UpdateChecker().check("0.4.0")
    opener.body = json.dumps([release("0.5.0", body="\x1b[31m说明\r\n第二行")]).encode()
    status = updates.UpdateChecker().check("0.4.0")
    assert "\x1b" not in status.release.notes and "说明\n第二行" in status.release.notes


def test_cli_check_uses_only_update_path(monkeypatch, capsys):
    monkeypatch.setattr(cli, "__version__", "0.4.0")
    monkeypatch.setattr(updates, "_read_releases", lambda: [release("0.5.0")])
    monkeypatch.setattr(cli.config.Config, "load", lambda: pytest.fail("unexpected access to user config"))
    assert cli.main(["check-updates"]) == 0
    assert "发现新版本 v0.5.0" in capsys.readouterr().out
