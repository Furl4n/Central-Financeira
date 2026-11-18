# Central Financeira

Backend local em Python/FastAPI, com PostgreSQL e integração somente leitura
com Pluggy. Contas, transações, faturas e sincronizações já implementadas.

## Executar

Requisitos: Docker com Compose, uv e Python 3.13 ou 3.14.
Na raiz do projeto:

```powershell
docker compose up -d --wait db
cd backend
uv sync --python 3.13
uv run alembic upgrade head
```

Para usar as credenciais já configuradas na PoC e persistir os dados no banco local:

```powershell
uv run --env-file ../poc-pluggy/.env python -m app.cli
```

Alternativamente, copie `backend/.env.example` para `backend/.env` e configure
localmente as variáveis. A URL padrão corresponde ao banco do Compose;
DATABASE_URL pode sobrescrevê-la. Nunca compartilhe os arquivos .env.

Iniciar a API, na pasta backend:

```powershell
uv run uvicorn app.api:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

Documentação interativa: http://127.0.0.1:8000/docs.
A API entrega dados financeiros reais ao navegador local; eles não são logs.
Não há autenticação de usuários nem configuração para exposição pública.

| Endpoint | Uso |
|---|---|
| GET /health | Disponibilidade do banco |
| GET /accounts | Contas; filtros type e connection_id |
| GET /transactions | Transações; filtros account_id, status, direction, date_from e date_to |
| GET /statements | Faturas; filtro account_id |
| GET /sync-status | Conexões, atualização na fonte, último sucesso e última execução |

Listas financeiras usam limit (1–200, padrão 50) e offset, com total e ordenação
estável. Datas de filtro exigem fuso, por exemplo `2026-11-01T00:00:00-03:00`.
Dinheiro é serializado como string decimal para preservar precisão. raw_amount
preserva a convenção da fonte; flow_amount usa DEBIT negativo e CREDIT positivo.
O pagamento de fatura é sinalizado, mas sua contrapartida bancária ainda não é
reconciliada automaticamente. Não há total consolidado de despesas nesta etapa.

O comando de sincronização é manual e consulta todas as páginas disponíveis,
sem forçar atualização bancária. Ele não exclui registros ausentes da janela da
fonte, nem gera parcelas futuras. Falhas mantêm os dados anteriores e registram
um código controlado. O banco não contém Client Secret ou API Key. Dados
financeiros persistem no volume Docker local; a configuração atual não adiciona
criptografia ao volume. A senha no Compose é apenas do PostgreSQL local.

## Verificar

Na pasta backend, com o PostgreSQL em execução:

```powershell
uv run pytest -q
uv run ruff check app tests migrations
uv run alembic check
```

Testes usam dados fictícios em schemas temporários com nomes aleatórios e
removem somente esses schemas ao terminar. TEST_DATABASE_URL pode apontar para
um PostgreSQL de testes separado. Cobrem migração, precisão, idempotência,
rollback, concorrência, paginação, validação e API.

Se o ambiente restringir o cache global do uv, acrescente
`--cache-dir .uv-cache` imediatamente depois de `uv`.

Para parar o banco preservando os dados: `docker compose stop db` na raiz.

Modelo e regras: [docs/modelo-de-dados.md](docs/modelo-de-dados.md).
Investigação inicial: [poc-pluggy/RESULTADOS.md](poc-pluggy/RESULTADOS.md).
