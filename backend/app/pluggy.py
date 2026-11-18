import json
from datetime import datetime, timezone
from decimal import Decimal

import httpx


class SyncError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class PluggyClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client = httpx.Client(base_url="https://api.pluggy.ai", timeout=30, follow_redirects=False)
        self.credentials = {"clientId": client_id, "clientSecret": client_secret}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def request(self, path, body=None):
        try:
            response = self.client.request("POST" if body else "GET", path, json=body)
        except httpx.HTTPError:
            raise SyncError("NETWORK_ERROR") from None
        if response.status_code != 200:
            raise SyncError(f"PLUGGY_HTTP_{response.status_code}")
        try:
            data = json.loads(response.content, parse_float=Decimal)
        except (ValueError, UnicodeError):
            raise SyncError("INVALID_JSON") from None
        if not isinstance(data, dict):
            raise SyncError("INVALID_RESPONSE")
        return data

    def authenticate(self):
        key = self.request("/auth", self.credentials).get("apiKey")
        if not isinstance(key, str) or not key:
            raise SyncError("INVALID_AUTH_RESPONSE")
        self.client.headers["X-API-KEY"] = key

    def records(self, path, params, cursor=False):
        query = str(httpx.QueryParams(params if cursor else {**params, "page": 1, "pageSize": 500}))
        suffix = "?" + query
        seen = set()
        page = 1
        while True:
            if suffix in seen or len(seen) >= 10000:
                raise SyncError("INVALID_PAGINATION")
            seen.add(suffix)
            data = self.request(path + suffix)
            rows = data.get("results")
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise SyncError("INVALID_LIST")
            yield from rows
            if cursor:
                if "next" not in data:
                    raise SyncError("MISSING_CURSOR")
                suffix = data["next"]
                if suffix is None:
                    return
                if not isinstance(suffix, str) or not suffix.startswith("?") or "#" in suffix:
                    raise SyncError("INVALID_CURSOR")
            else:
                total = data.get("totalPages")
                if not isinstance(total, int) or isinstance(total, bool) or total < 0:
                    raise SyncError("INVALID_PAGINATION")
                if page >= total:
                    return
                page += 1
                suffix = "?" + str(httpx.QueryParams({**params, "page": page, "pageSize": 500}))

    def fetch(self, item_id):
        from urllib.parse import quote

        self.authenticate()
        item = self.request("/items/" + quote(item_id, safe=""))
        expiry = item.get("consentExpiresAt")
        if expiry:
            try:
                expired = datetime.fromisoformat(expiry.replace("Z", "+00:00")) <= datetime.now(timezone.utc)
            except (ValueError, TypeError, AttributeError):
                raise SyncError("INVALID_CONSENT_DATE") from None
            if expired:
                raise SyncError("CONSENT_EXPIRED")
        if item.get("status") not in ("UPDATED", "PARTIAL_SUCCESS"):
            raise SyncError("ITEM_NOT_READY")
        accounts = list(self.records("/accounts", {"itemId": item_id}))
        if not accounts:
            raise SyncError("EMPTY_ACCOUNTS")
        transactions, bills = {}, {}
        for account in accounts:
            account_id = account.get("id")
            if not isinstance(account_id, str) or not account_id:
                raise SyncError("INVALID_ACCOUNT_ID")
            params = {"accountId": account_id}
            transactions[account_id] = list(self.records("/v2/transactions", params, cursor=True))
            bills[account_id] = (
                list(self.records("/bills", params)) if account.get("type") == "CREDIT" else []
            )
        return {"item": item, "accounts": accounts, "transactions": transactions, "bills": bills}
