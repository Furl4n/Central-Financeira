# Validação Pluggy — Fase 0

## Estado

Documentação oficial consultada em 18/11/2026. Consulta real executada com sucesso
na mesma data: autenticação, conexão, contas bancária e de cartão, saldos,
transações de ambas as contas e faturas. Paginação concluída sem erros.
Credenciais carregadas do .env com uv; cache local usado por restrição de acesso
ao cache global. Nenhum valor financeiro ou identificador foi gravado.

Verificação local: 7 testes automatizados com dados fictícios passaram, cobrindo
paginação, precisão decimal, sanitização de erros/relatório, falha em faturas,
respostas vazias e leitura essencial bem-sucedida. A execução sem configuração
encerrou com orientação para definir as três variáveis, sem chamar a API.

| Recurso | Endpoint oficial | Disponível? | Campos úteis | Limitações / evidência |
|---|---|---|---|---|
| Autenticação | POST /auth | Confirmado em teste real | apiKey | Token server-side de 2 horas |
| Listagem de conexões | GET /v2/items | Indisponível para Meu Pluggy | — | Copiar itemId no Dashboard; não chamado pela PoC |
| Conexão autorizada | GET /items/{id} | Confirmado em teste real | status, lastUpdatedAt, updatedAt, consentExpiresAt, connector | Instituição deve ser conferida no Dashboard |
| Contas / saldos | GET /accounts?itemId=… | Confirmado em teste real | id, type, subtype, balance, currencyCode, bankData, creditData | Paginação concluída; saldo CREDIT não é dinheiro disponível |
| Transações | GET /v2/transactions?accountId=… | Confirmado em ambas as contas | id, date, amount, description, status, type, currencyCode, creditCardMetadata | Cursor next até null; extensão temporal ainda não avaliada |
| Cartão / limites | GET /accounts?itemId=… | Confirmado em teste real | creditData.creditLimit, availableCreditLimit, balanceDueDate, minimumPayment, disaggregatedCreditLimits | balanceCloseDate ausente na amostra |
| Faturas | GET /bills?accountId=… | Confirmado em teste real | dueDate, billClosingDate, totalAmount, minimumPaymentAmount, payments | Consulta de conta CREDIT com paginação concluída |

## Condições verificadas na documentação

- Uso pessoal: gratuito, até 5 conexões, sem uso comercial; não termina junto
  com o trial. Isso sustenta a viabilidade documental, não confirma o acesso
  desta aplicação nem seus dados do Nubank.
- É necessário autorizar o conector MeuPluggy na aplicação do Dashboard.
  As conexões espelham o Meu Pluggy a cada 24 horas e não permitem atualização
  manual pela API.
- Autorização de leitura do MeuPluggy dura um ano, separada do consentimento de
  cada banco. Ao expirar, listas podem ficar vazias mesmo antes de o status do
  item mudar. Renovar no Dashboard e conferir novamente o itemId.
- API Key dura 2 horas; credenciais de aplicação não devem ir para frontend.
- Transações usam next como query string pronta. O endpoint antigo
  GET /transactions está descontinuado, com retirada anunciada para 31/12/2026;
  não é usado nesta PoC.
- Listas por página usam page/pageSize, com até 500 registros por página.
- A referência informa limites por endpoint/IP/minuto (360 para autenticação,
  contas e transações na tabela consultada), com HTTP 429 e cabeçalhos de espera.
  Limites de consulta da API e atualização na instituição são coisas distintas.
- Gratuidade não implica acesso aos produtos pagos de inteligência, como
  enriquecimento e categorização; a PoC não depende deles.

Leitura essencial validada. Inspeção complementar confirmou campos de limites,
parcelas e vínculos de fatura; conclusões em [modelo mínimo](../docs/modelo-de-dados.md).
Pendentes: extensão temporal do histórico, reconciliação automática de pagamentos,
identificação da instituição
e condições efetivas do plano no Dashboard. A gratuidade foi confirmada na
documentação; esta execução não verifica faturamento nem mudanças futuras do plano.

## Fontes oficiais

- [Uso pessoal, gratuidade, configuração, frequência e consentimento](https://docs.pluggy.ai/en/docs/guides/meu-pluggy-personal-use)
- [Autenticação](https://docs.pluggy.ai/en/reference/authentication)
- [Conceitos e paginação](https://docs.pluggy.ai/en/reference/basic-concepts)
- [Transações v2](https://docs.pluggy.ai/en/reference/transaction/transactions-list-by-cursor)
- [Contas](https://docs.pluggy.ai/en/reference/account/accounts-list)
- [Faturas](https://docs.pluggy.ai/en/reference/bill/bills-list)
- [Limites de requisição](https://docs.pluggy.ai/en/reference/rate-limits)
- [Plano gratuito e produtos pagos](https://v2.docs.pluggy.ai/en/docs/get-started/contact)
