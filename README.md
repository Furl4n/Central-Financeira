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

## Dashboard

Com a API em execução na porta 8000, abra outro terminal na raiz:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Acesse http://127.0.0.1:5173. O dashboard apresenta contas e crédito separados,
movimentações com filtros e paginação, faturas e estado das conexões. É possível
ocultar valores. “Recarregar dados” consulta o banco local; uma nova importação
do Pluggy continua sendo feita pelo comando de sincronização do backend.

O Vite encaminha `/api` ao backend local; o navegador não recebe credenciais
Pluggy. Não há persistência dos dados financeiros em localStorage, fontes
remotas ou serviços de análise. `npm.cmd run build` verifica TypeScript e gera
o build. O frontend foi preparado para desenvolvimento local; o build isolado
precisa de um servidor que encaminhe `/api` para o backend.

O cartão “A pagar” usa GET /payables: soma por moeda o restante das faturas
(total menos pagamentos registrados, limitado a zero) e compras PENDING sem
fatura, descontando os créditos dessas compras por conta/moeda. Não soma o saldo
do cartão nem transações já vinculadas a faturas. É uma estimativa dos registros
disponíveis. Compras internacionais usam o valor na moeda da conta informado
pelo banco (`amountInAccountCurrency`); se ele não estiver disponível, conservam
a moeda original, sem conversão por cotação inventada. Atrasos, refinanciamentos
e saldos carregados entre faturas exigem
conciliação para confirmar a dívida efetiva. **Boletos pendentes ainda não estão
integrados nem incluídos neste total**, pois o Pluggy não oferece consulta DDA.
Essa limitação fica documentada aqui, sem aviso adicional na interface.

Testes de navegador, com respostas fictícias e sem consultar suas contas:

```powershell
npx.cmd playwright install chromium
npm.cmd test
```

No Windows, também é possível usar o Edge instalado, sem baixar Chromium:
`$env:PLAYWRIGHT_CHANNEL = 'msedge'` antes de `npm.cmd test`.

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
