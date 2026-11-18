# PoC Meu Pluggy

Consulta somente leitura, sem frontend, banco ou dependências externas. Autentica,
consulta o item autorizado e percorre contas, transações e, para contas CREDIT,
faturas. Dados reais ficam apenas na memória; o relatório contém contagens e
nomes de campos, sem valores financeiros, descrições, IDs ou tokens.

## Preparação

Requisitos: Python 3.13+ e uv. Se necessário, instale uv seguindo
[as instruções oficiais](https://docs.astral.sh/uv/getting-started/installation/).

No [Dashboard Pluggy](https://dashboard.pluggy.ai), abra Applications → sua
aplicação → Demo → Connect Account e selecione **MeuPluggy**. Autorize com a conta
usada no Meu Pluggy. Conectar o Nubank somente no Meu Pluggy e criar as chaves não
substitui essa autorização. Em Connected Items, confira a instituição e copie o
itemId correspondente ao Nubank. A modalidade pessoal não permite GET /v2/items.

Na pasta desta PoC:

```powershell
Copy-Item .env.example .env
```

Preencha `.env` localmente no editor, sem compartilhar seu conteúdo:
`PLUGGY_CLIENT_ID`, `PLUGGY_CLIENT_SECRET` e `PLUGGY_ITEM_ID`.
O arquivo é ignorado pelo Git. O código lê variáveis de ambiente; uv carrega o
arquivo com a opção abaixo. Não é necessário inserir segredos no terminal.

## Execução

```powershell
uv run --env-file .env python main.py
```

O resultado vai para `resultado-local.md`, ignorado pelo Git. Mesmo sanitizado,
o relatório informa quantidades de registros: revise antes de compartilhar.
As chamadas vão exclusivamente para `https://api.pluggy.ai`; não há atualização
forçada, criação de conexões ou movimentação de dinheiro. Redirecionamentos são
recusados. O token é reutilizado durante a execução e descartado ao encerrar.

Saídas: `0` leitura essencial confirmada sem falhas; `1` validação incompleta
(inclusive falha em produto opcional); `2` configuração ausente ou erro local.
Uma lista vazia não comprova disponibilidade de transações. Instituição e
condições do plano devem ser conferidas no Dashboard; o código não verifica cobrança.
Em erro HTTP, imprime apenas código e explicação controlada. Em 429, aguarde
antes de repetir; não há repetição automática. Uma falha em uma conta não impede
a consulta das demais. A PoC não implementa sincronização incremental nem renova
tokens automaticamente; isso fica para o backend.

Também é possível executar `python main.py` com as três variáveis já configuradas
no processo, sem uv. Python sozinho não carrega `.env`.

## Testes com dados fictícios

```powershell
uv run python -m unittest -v
```

Ou `python -m unittest -v`. Não faz chamadas de rede.

Fontes, limitações e estado da validação: [RESULTADOS.md](RESULTADOS.md).

Para conferir presença de campos de limites, parcelas e pagamentos, sem imprimir
valores ou identificadores: `uv run --env-file .env python inspect_schema.py`.
A inspeção faz novas consultas somente leitura e exibe contagens em memória.
