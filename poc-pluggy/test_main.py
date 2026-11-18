import io
import unittest
from decimal import Decimal
from unittest.mock import patch
from urllib.error import HTTPError

from main import Client, ProbeError, probe


class ProbeTests(unittest.TestCase):
    def test_cursor_keeps_query_and_reads_all_pages(self):
        client = Client()
        with patch.object(client, "request", side_effect=[
            {"results": [{"id": "a"}], "next": "?accountId=x&after=abc%2Bdef"},
            {"results": [{"id": "b"}], "next": None},
        ]) as request:
            self.assertEqual(len(list(client.records("/v2/transactions", {"accountId": "x"}, True))), 2)
            self.assertEqual(request.call_args.args[0], "/v2/transactions?accountId=x&after=abc%2Bdef")

    def test_page_pagination_and_repeated_cursor(self):
        client = Client()
        with patch.object(client, "request", side_effect=[
            {"results": [{"id": "a"}], "totalPages": 2},
            {"results": [{"id": "b"}], "totalPages": 2},
        ]):
            self.assertEqual(len(list(client.records("/accounts", {"itemId": "x"}))), 2)
        with patch.object(client, "request", return_value={"results": [], "next": "?accountId=x"}):
            with self.assertRaises(ProbeError):
                list(client.records("/v2/transactions", {"accountId": "x"}, True))

    def test_http_error_does_not_leak_body_or_url(self):
        client = Client()
        error = HTTPError("https://api.pluggy.ai/accounts?itemId=private", 403,
                          "private", {}, io.BytesIO(b'private-secret'))
        with patch.object(client.opener, "open", side_effect=error):
            with self.assertRaises(ProbeError) as caught:
                client.request("/accounts")
        self.assertNotIn("private", str(caught.exception))
        self.assertIn("403", str(caught.exception))

    def test_decimal_precision(self):
        client = Client()
        response = io.BytesIO(b'{"balance": 123.4567890123456789}')
        with patch.object(client.opener, "open", return_value=response):
            self.assertEqual(client.request("/accounts")["balance"], Decimal("123.4567890123456789"))

    def test_report_omits_values_and_handles_card_failure(self):
        client = Client()
        responses = [
            {"apiKey": "secret-key"},
            {"status": "UPDATED", "consentExpiresAt": "2099-01-01T00:00:00Z"},
            {"results": [{"id": "private-account", "type": "BANK", "balance": Decimal("1234.56")},
                         {"id": "private-card", "type": "CREDIT"}], "totalPages": 1},
            {"results": [{"id": "private-tx", "amount": 42, "description": "private-shop"}], "next": None},
            {"results": [], "next": None},
            ProbeError("HTTP 403: acesso não autorizado"),
        ]
        with patch.object(client, "request", side_effect=responses):
            report, success = probe(client, ("private-client", "private-secret", "private-item"))
        self.assertFalse(success)
        for secret in ("private-", "1234.56", "secret-key"):
            self.assertNotIn(secret, report)
        self.assertIn("HTTP 403", report)
        self.assertIn("1 transações", report)

    def test_empty_accounts_do_not_confirm_success(self):
        client = Client()
        with patch.object(client, "request", side_effect=[
            {"apiKey": "secret"}, {}, {"results": [], "totalPages": 0},
        ]):
            report, success = probe(client, ("client", "secret", "item"))
        self.assertFalse(success)
        self.assertIn("resposta vazia", report)

    def test_successful_essential_read(self):
        client = Client()
        with patch.object(client, "request", side_effect=[
            {"apiKey": "secret"}, {"status": "UPDATED"},
            {"results": [{"id": "account", "type": "BANK", "balance": 0}], "totalPages": 1},
            {"results": [{"id": "tx", "amount": 10}], "next": None},
        ]):
            report, success = probe(client, ("client", "secret", "item"))
        self.assertTrue(success)
        self.assertIn("Leitura essencial confirmada", report)


if __name__ == "__main__":
    unittest.main()
