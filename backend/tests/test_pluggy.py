import httpx
import pytest

from app.pluggy import PluggyClient, SyncError


def mocked_client(handler):
    client = PluggyClient("fake", "fake")
    client.client.close()
    client.client = httpx.Client(base_url="https://api.pluggy.ai", transport=httpx.MockTransport(handler))
    return client


def test_cursor_preserves_encoded_query_and_auth_header():
    paths = []

    def handler(request):
        paths.append(request.url.raw_path)
        if request.url.path == "/auth":
            return httpx.Response(200, json={"apiKey": "fake-key"})
        assert request.headers["X-API-KEY"] == "fake-key"
        if "after" not in request.url.params:
            return httpx.Response(200, json={"results": [{"id": "one"}], "next": "?accountId=a&after=x%2By"})
        return httpx.Response(200, json={"results": [{"id": "two"}], "next": None})

    with mocked_client(handler) as client:
        client.authenticate()
        assert len(list(client.records("/v2/transactions", {"accountId": "a"}, cursor=True))) == 2
    assert paths[-1] == b"/v2/transactions?accountId=a&after=x%2By"


def test_page_failure_does_not_return_partial_list():
    def handler(request):
        if request.url.params.get("page") == "1":
            return httpx.Response(200, json={"results": [{"id": "one"}], "totalPages": 2})
        return httpx.Response(429, text="sensitive body")

    with mocked_client(handler) as client:
        with pytest.raises(SyncError, match="^PLUGGY_HTTP_429$"):
            list(client.records("/accounts", {"itemId": "fake"}))


def test_redirect_never_follows_secret_to_other_host():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(302, headers={"location": "https://other.invalid/"})

    with mocked_client(handler) as client:
        client.client.headers["X-API-KEY"] = "secret"
        with pytest.raises(SyncError, match="PLUGGY_HTTP_302"):
            client.request("/accounts")
    assert len(requests) == 1


def test_expired_consent_blocks_reads():
    def handler(request):
        if request.url.path == "/auth":
            return httpx.Response(200, json={"apiKey": "fake"})
        assert request.url.path == "/items/fake"
        return httpx.Response(200, json={"status": "UPDATED", "consentExpiresAt": "2000-01-01T00:00:00Z"})

    with mocked_client(handler) as client:
        with pytest.raises(SyncError, match="CONSENT_EXPIRED"):
            client.fetch("fake")


def test_invalid_cursor_cannot_change_host():
    with mocked_client(
        lambda request: httpx.Response(200, json={"results": [], "next": "https://other.invalid/"})
    ) as client:
        with pytest.raises(SyncError, match="INVALID_CURSOR"):
            list(client.records("/v2/transactions", {"accountId": "a"}, cursor=True))
