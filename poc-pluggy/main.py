"""PoC somente leitura. Nunca imprime respostas, identificadores ou valores."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


class ProbeError(Exception):
    """Mensagem controlada, sem conteúdo retornado pela API."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self):
        self.key = None
        self.opener = build_opener(NoRedirect)

    def request(self, path, body=None):
        headers = {"Accept": "application/json"}
        if self.key:
            headers["X-API-KEY"] = self.key
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        request = Request("https://api.pluggy.ai" + path, data=data, headers=headers)
        try:
            with self.opener.open(request, timeout=30) as response:
                payload = json.loads(response.read(), parse_float=Decimal)
        except HTTPError as error:
            hints = {401: "credenciais ou token inválidos", 403: "acesso não autorizado",
                     404: "recurso não encontrado", 410: "endpoint indisponível",
                     429: "limite de consultas; aguarde antes de executar novamente"}
            raise ProbeError(f"HTTP {error.code}: {hints.get(error.code, 'consulta recusada')}") from None
        except (URLError, TimeoutError, OSError):
            raise ProbeError("Falha de rede ou timeout; resposta não registrada") from None
        except (ValueError, UnicodeError):
            raise ProbeError("Resposta JSON inválida; conteúdo não registrado") from None
        if not isinstance(payload, dict):
            raise ProbeError("Formato de resposta inesperado")
        return payload

    def records(self, path, params, cursor=False):
        page = 1
        suffix = "?" + urlencode(params if cursor else {**params, "page": page, "pageSize": 500})
        seen = set()
        while True:
            if suffix in seen or len(seen) >= 10000:
                raise ProbeError("Paginação repetida ou limite de segurança atingido")
            seen.add(suffix)
            payload = self.request(path + suffix)
            rows = payload.get("results")
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise ProbeError("Formato inesperado na lista de registros")
            yield from rows
            if cursor:
                if "next" not in payload:
                    raise ProbeError("Cursor ausente na resposta")
                suffix = payload["next"]
                if suffix is None:
                    return
                if not isinstance(suffix, str) or not suffix.startswith("?") or "#" in suffix:
                    raise ProbeError("Formato inesperado no cursor")
            else:
                total_pages = payload.get("totalPages")
                if not isinstance(total_pages, int) or isinstance(total_pages, bool) or total_pages < 0:
                    raise ProbeError("Metadados de paginação inválidos")
                if page >= total_pages:
                    return
                page += 1
                suffix = "?" + urlencode({**params, "page": page, "pageSize": 500})


def load_config():
    names = ("PLUGGY_CLIENT_ID", "PLUGGY_CLIENT_SECRET", "PLUGGY_ITEM_ID")
    missing = [name for name in names if not os.environ.get(name, "").strip()]
    if missing:
        raise ProbeError("Configure localmente: " + ", ".join(missing))
    return tuple(os.environ[name].strip() for name in names)


def summarize(rows, fields):
    count = 0
    found = set()
    for row in rows:
        count += 1
        found.update(field for field in fields if row.get(field) is not None)
    return count, ", ".join(sorted(found)) or "nenhum campo confirmado"


def probe(client, config):
    client_id, secret, item_id = config
    lines = ["# Resultado local — PoC Pluggy", "",
             "Execução UTC: " + datetime.now(timezone.utc).isoformat(), "",
             "Somente metadados; nenhum saldo, identificador ou extrato é gravado.", "",
             "| Recurso | Endpoint | Resultado | Campos presentes (sem valores) |",
             "|---|---|---|---|"]
    failures = False

    def record(resource, endpoint, operation):
        nonlocal failures
        try:
            result, fields = operation()
            lines.append(f"| {resource} | `{endpoint}` | {result} | {fields} |")
            return True
        except ProbeError as error:
            failures = True
            lines.append(f"| {resource} | `{endpoint}` | {error} | não verificado |")
            return False

    def auth():
        payload = client.request("/auth", {"clientId": client_id, "clientSecret": secret})
        key = payload.get("apiKey")
        if not isinstance(key, str) or not key:
            raise ProbeError("Autenticação sem apiKey válida")
        client.key = key
        return "autenticado", "apiKey (mantida apenas em memória)"

    if not record("Autenticação", "POST /auth", auth):
        return "\n".join(lines) + "\n", False

    def item():
        payload = client.request("/items/" + quote(item_id, safe=""))
        expiry = payload.get("consentExpiresAt")
        if expiry:
            try:
                expired = datetime.fromisoformat(expiry.replace("Z", "+00:00")) <= datetime.now(timezone.utc)
            except (TypeError, ValueError, AttributeError):
                raise ProbeError("Data de consentimento inválida") from None
            if expired:
                raise ProbeError("Consentimento expirado; autorize MeuPluggy novamente no Dashboard")
        fields = [field for field in ("status", "lastUpdatedAt", "updatedAt", "consentExpiresAt", "connector", "statusDetail") if payload.get(field) is not None]
        return "consultado; instituição deve ser conferida no Dashboard", ", ".join(fields)

    record("Conexão", "GET /items/{id}", item)
    accounts = []

    def fetch_accounts():
        accounts.extend(client.records("/accounts", {"itemId": item_id}))
        count, fields = summarize(accounts, ("id", "type", "subtype", "balance", "currencyCode", "bankData", "creditData"))
        return (f"{count} contas" if count else "resposta vazia; acesso essencial não confirmado"), fields

    accounts_ok = record("Contas e saldos", "GET /accounts", fetch_accounts)
    essential = accounts_ok and any(a.get("type") == "BANK" and a.get("balance") is not None for a in accounts)
    confirmed_transactions = False
    for index, account in enumerate(accounts, 1):
        account_id = account.get("id")
        if not isinstance(account_id, str) or not account_id:
            failures = True
            continue
        params = {"accountId": account_id}

        def transactions():
            nonlocal confirmed_transactions
            count, fields = summarize(client.records("/v2/transactions", params, cursor=True),
                                      ("id", "date", "description", "amount", "type", "status", "currencyCode", "creditCardMetadata", "providerId"))
            if account.get("type") == "BANK" and count:
                confirmed_transactions = True
            return f"{count} transações; paginação concluída", fields

        record(f"Transações da conta {index}", "GET /v2/transactions", transactions)
        if account.get("type") == "CREDIT":
            def bills():
                count, fields = summarize(client.records("/bills", params),
                                          ("id", "dueDate", "billClosingDate", "totalAmount", "minimumPaymentAmount", "payments"))
                return f"{count} faturas; paginação concluída", fields
            record(f"Faturas da conta {index}", "GET /bills", bills)
    if not any(a.get("type") == "CREDIT" for a in accounts):
        lines.append("| Cartão/faturas | GET /bills | não testado: nenhuma conta CREDIT retornada | — |")
    success = essential and confirmed_transactions and not failures
    lines.extend(["", "Leitura essencial confirmada." if success else "Validação incompleta; confira os resultados acima.",
                  "Gratuidade e limites do plano: consultar RESULTADOS.md; esta execução não verifica faturamento."])
    return "\n".join(lines) + "\n", success


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("resultado-local.md"))
    args = parser.parse_args()
    try:
        config = load_config()
        report, success = probe(Client(), config)
        args.output.write_text(report, encoding="utf-8")
    except ProbeError as error:
        print(str(error), file=sys.stderr)
        return 2
    except OSError:
        print("Não foi possível gravar o relatório local.", file=sys.stderr)
        return 2
    print("Consulta concluída. Relatório sanitizado gravado localmente.")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
