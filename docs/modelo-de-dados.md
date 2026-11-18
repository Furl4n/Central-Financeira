# Modelo mínimo do backend

Baseado na consulta real de 18/11/2026. Escopo: persistir contas, transações,
faturas e estado da sincronização; expor leitura pelo FastAPI. Sem obrigações,
recorrências ou simuladores nesta etapa.

## Entidades

Todas usam UUID local. Identificadores externos são strings; não usar descrições,
datas ou valores como chave de deduplicação. Valores monetários usam Decimal e
NUMERIC, sem conversão intermediária para float. Datas da API são preservadas
como instantes com fuso (TIMESTAMPTZ); vencimento de fatura é uma data (DATE).
Preservar também o texto temporal original quando a conversão for ambígua.

| Entidade | Dados essenciais | Identidade / relação |
|---|---|---|
| BankConnection | provider, external_id, institution_name, provider_status, last_provider_update_at, consent_expires_at, last_successful_sync_at | UNIQUE(provider, external_id) |
| Account | connection_id, external_id, type, subtype, name, currency, balance, balance_observed_at; credit_limit e available_credit_limit opcionais | UNIQUE(connection_id, external_id) |
| Transaction | account_id, external_id, provider_id opcional, description, occurred_at, source_date, raw_amount, direction, currency, status, operation_type, provider_created_at, provider_updated_at, first_seen_at, last_seen_at | UNIQUE(account_id, external_id) |
| CardStatement | account_id, external_id, due_date, closing_date opcional, total_amount, currency, minimum_payment opcional | UNIQUE(account_id, external_id) |
| SyncExecution | connection_id, started_at, finished_at, status, contagens por recurso, error_code controlado | Histórico de execuções, sem payloads ou mensagens externas |

Campos opcionais em Transaction para cartão: installment_number,
total_installments, purchase_date, purchase_total_amount, external_bill_id e
statement_id anulável. Guardar external_bill_id mesmo quando a fatura ainda não
existir localmente; reconciliar a FK ao recebê-la. Não criar entidade Card
separada: a conta CREDIT já representa o cartão neste primeiro incremento.

CardStatement conserva payments em JSONB limitado aos campos paymentDate,
amount, paymentMode e valueType, validado com Pydantic e serialização decimal
sem perda. São evidências de liquidação, não novas transações. Não persistir
payloads completos nem dados de participantes de transferências nesta etapa.

Account mantém o último saldo observado. Um histórico de snapshots pode ser
introduzido quando houver uma funcionalidade que o utilize; o histórico anterior
não pode ser reconstruído somando um extrato cuja cobertura é incompleta.

## Regras financeiras

1. **Saldo disponível:** somar somente contas BANK, agrupadas por moeda. Exibir
   saldo/limite do cartão separadamente. Não somar limite de crédito ao dinheiro
   disponível nem tratar balance CREDIT como total da próxima fatura.
2. **Sinais:** preservar raw_amount. Para análise de entrada/saída, usar direction
   DEBIT/CREDIT e magnitude absoluta. Não deduzir direção apenas do sinal: as
   compras do cartão têm convenção diferente das despesas bancárias.
3. **Confirmado e pendente:** conservar PENDING/POSTED. No cartão, POSTED indica
   lançamento consolidado em fatura, não que a fatura esteja paga. Mostrar os dois
   estados separadamente; não descartar compras pendentes do histórico.
4. **Pagamento de fatura:** operation_type PAGAMENTO_FATURA no cartão liquida
   dívida; não é renda. No orçamento de consumo, compras contam como gastos e
   pagamentos de fatura não contam novamente. No fluxo bancário, o débito do
   pagamento continua sendo saída de caixa. Enquanto a contrapartida bancária
   não for reconciliada com confiança, não publicar um total consolidado de
   despesas misturando contas bancárias e cartões.
5. **Estornos/cashback:** CREDIT no cartão não significa automaticamente renda
   ou pagamento de fatura. Preservar operation_type e classificar explicitamente;
   casos desconhecidos permanecem sem classificação.
6. **Parcelas:** conservar os campos recebidos. Não multiplicar a parcela pelo
   total para apresentar um custo exato da compra e não inventar parcelas
   futuras. Não há identificador confiável de grupo de compra validado.
7. **Transferências internas:** não classificar todo PIX ou transferência como
   movimentação entre contas próprias. Reconciliar depois; preservar origem e
   evitar classificação definitiva com base apenas em descrição ou valor.

## Sincronização e primeiro incremento

- Buscar item, contas, todas as páginas de transações v2 e faturas antes de
  atualizar o conjunto financeiro no PostgreSQL. Falha em qualquer recurso
  impede publicação de um estado parcialmente atualizado.
- Fazer upsert por identidade externa, atualizando campos mutáveis, incluindo
  mudanças de PENDING para POSTED e vínculos de fatura. Uma repetição sem
  alterações não cria novas linhas.
- Registrar SyncExecution separadamente, inclusive quando houver rollback.
  Atualizar last_successful_sync_at apenas após commit; guardar o horário da
  fonte separado do horário em que consultamos a API.
- Começar com leitura completa do histórico disponível: filtrar só os últimos
  dias perderia alterações antigas. Não excluir registros por ausência numa
  consulta, pois a janela da fonte pode mudar. Exclusões explícitas e troca de
  itemId exigirão reconciliação própria; não afirmar que ausência é exclusão.
- Uma sincronização por conexão de cada vez. Nenhuma atualização forçada na
  instituição; consultar Pluggy não significa que o banco acabou de atualizar.
- Credenciais por ambiente; API Key somente em memória. Sem logs de respostas
  ou parâmetros pessoais. API local vinculada a 127.0.0.1.

Implementação seguinte: FastAPI + SQLAlchemy + Alembic, PostgreSQL via Docker
Compose; comando local de sincronização e endpoints GET /accounts,
GET /transactions (filtros e paginação), GET /statements e GET /sync-status.
Sincronização começa por comando, sem endpoint público que dispare chamadas.

Aceite: duas sincronizações não duplicam registros; alteração de status/fatura
atualiza a linha; falha numa página mantém o estado anterior; dinheiro mantém
precisão; cartão não infla saldo disponível. Testes com dados fictícios.

## Evidência e limites

Na amostra real: sinais observados são negativos para DEBIT bancário e positivos
para DEBIT do cartão; providerId não veio preenchido. Há metadados de parcelas
com installmentNumber, totalInstallments e purchaseDate, mas sem totalAmount.
Os billId presentes apontam para faturas retornadas. Há compras PENDING sem
fatura e pagamentos com PAGAMENTO_FATURA. creditLimit e availableCreditLimit
estão presentes; balanceCloseDate não. Pagamentos de fatura não trazem
transactionId para ligar diretamente ao débito bancário.

Essas constatações descrevem a amostra, não garantem o mesmo formato para todos
os bancos, atualizações futuras ou contas. Ainda não foi comprovada uma regra
automática de reconciliação entre pagamento bancário e cartão.

Referências oficiais:
[transações e sinais](https://v2.docs.pluggy.ai/en/docs/products/transactions),
[ciclo de faturas e parcelas](https://v2.docs.pluggy.ai/en/docs/products/credit-card-installments),
[semântica de saldos](https://v2.docs.pluggy.ai/en/docs/products/accounts).
