import { useState } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Building2,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  CreditCard,
  Eye,
  EyeOff,
  FileText,
  Landmark,
  LayoutDashboard,
  Link2,
  LoaderCircle,
  RefreshCw,
  Wallet,
  AlertCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { allPages, request, useResource } from "./api";
import { dateLabel, isOld, money, timestamp, totals } from "./format";
import type {
  Account,
  Connection,
  Page,
  Statement,
  Transaction,
  Payables,
} from "./types";

type View = "overview" | "transactions" | "statements" | "connections";
const navigation: { id: View; label: string; icon: LucideIcon }[] = [
  { id: "overview", label: "Visão geral", icon: LayoutDashboard },
  { id: "transactions", label: "Movimentações", icon: ArrowDownLeft },
  { id: "statements", label: "Faturas", icon: FileText },
  { id: "connections", label: "Conexões", icon: Link2 },
];

function Amount({
  value,
  currency = "BRL",
  hidden,
}: {
  value: string | null;
  currency?: string;
  hidden: boolean;
}) {
  return (
    <span className="amount">{hidden ? "••••••" : money(value, currency)}</span>
  );
}
function Empty({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="empty">
      <Wallet size={30} strokeWidth={1.5} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
function Loading() {
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" size={22} /> Carregando seus dados…
    </div>
  );
}
function ErrorMessage({
  message,
  retry,
}: {
  message: string;
  retry: () => void;
}) {
  return (
    <div className="error" role="alert">
      <AlertCircle size={22} />
      <div>
        <strong>Não foi possível carregar</strong>
        <p>{message}</p>
        <button className="text-button" onClick={retry}>
          Tentar novamente
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const [view, setView] = useState<View>("overview");
  const [hidden, setHidden] = useState(false);
  const [revision, setRevision] = useState(0);
  const data = useResource(`dashboard-${revision}`, async (signal) => {
    const [accounts, connections] = await Promise.all([
      allPages<Account>("/accounts", signal),
      request<Connection[]>("/sync-status", signal),
    ]);
    return { accounts, connections };
  });
  const accounts = data.data?.accounts ?? [];
  const connections = data.data?.connections ?? [];
  const stale = connections.some((connection) =>
    isOld(connection.last_provider_update_at),
  );
  const failed = connections.some(
    (connection) => connection.latest_execution?.status === "FAILED",
  );
  const partial = connections.some(
    (connection) => connection.provider_status === "PARTIAL_SUCCESS",
  );
  const expired = connections.some(
    (connection) =>
      connection.consent_expires_at &&
      new Date(connection.consent_expires_at).getTime() < Date.now(),
  );
  const title = navigation.find((item) => item.id === view)!.label;
  const refresh = () => setRevision((value) => value + 1);
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Pular para o conteúdo
      </a>
      <aside className="sidebar">
        <a
          href="#"
          className="brand"
          onClick={(event) => {
            event.preventDefault();
            setView("overview");
          }}
          aria-label="Central, início"
        >
          <span className="brand-mark">
            <span />
            <span />
            <span />
          </span>
          central<span className="brand-period">.</span>
        </a>
        <p className="nav-label">ACOMPANHAR</p>
        <nav aria-label="Navegação principal">
          {navigation.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={`nav-item ${view === id ? "active" : ""}`}
              aria-current={view === id ? "page" : undefined}
              onClick={() => setView(id)}
            >
              <Icon size={19} strokeWidth={1.7} />
              <span>{label}</span>
              {id === "connections" && (
                <span className="nav-count">{connections.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="profile">
            <span className="avatar">P</span>
            <div>
              <strong>Conta pessoal</strong>
              <small>Central Financeira</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <main id="main">
          <div className="page-heading">
            <div>
              <h1>{title}</h1>
              <p>
                {view === "overview"
                  ? "Tudo o que você precisa acompanhar, em um só lugar."
                  : view === "transactions"
                    ? "Explore as movimentações das suas contas e cartões."
                    : view === "statements"
                      ? "Consulte as faturas e os pagamentos registrados."
                      : "Saiba de onde vêm seus dados e quando foram atualizados."}
              </p>
            </div>
            <button
              className="button secondary refresh"
              disabled={data.loading}
              onClick={refresh}
            >
              <RefreshCw size={16} className={data.loading ? "spin" : ""} />
              Recarregar dados
            </button>
          </div>
          {data.loading ? (
            <Loading />
          ) : data.error ? (
            <ErrorMessage message={data.error} retry={refresh} />
          ) : (
            <>
              {(stale || failed || partial || expired) && (
                <div className="notice">
                  <AlertCircle size={18} />
                  <span>
                    {expired
                      ? "O consentimento de uma conexão expirou. Renove a autorização no Pluggy para atualizar os dados."
                      : partial
                        ? "A instituição disponibilizou uma atualização parcial. Alguns dados podem estar desatualizados."
                        : failed
                          ? "A última sincronização falhou. Você está vendo os dados da última execução concluída."
                          : "A atualização bancária tem mais de 36 horas ou ainda não foi informada. Os dados podem estar desatualizados."}
                  </span>
                  <button onClick={() => setView("connections")}>
                    Ver conexão
                  </button>
                </div>
              )}
              {accounts.length === 0 && view !== "connections" ? (
                <Empty title="Seu ponto de partida está aqui">
                  Sincronize suas contas pelo comando local para começar a
                  acompanhar suas finanças.
                </Empty>
              ) : (
                <>
                  {view === "overview" && (
                    <>
                      <Overview
                        accounts={accounts}
                        hidden={hidden}
                        onToggleVisibility={() => setHidden((value) => !value)}
                        revision={revision}
                        onStatements={() => setView("statements")}
                      />
                      <div className="content-grid">
                        <section className="panel accounts-panel">
                          <div className="section-heading">
                            <div>
                              <h2>Suas contas</h2>
                            </div>
                            <span className="count-badge">
                              {accounts.length}
                            </span>
                          </div>
                          <div className="account-list">
                            {accounts.map((account) => (
                              <AccountCard
                                key={account.id}
                                account={account}
                                hidden={hidden}
                              />
                            ))}
                          </div>
                        </section>
                        <section className="panel source-panel">
                          <span className="source-symbol">
                            <Link2 size={22} />
                          </span>
                          <div>
                            <h2>Uma visão conectada</h2>
                            <p>
                              Seus dados chegam pelo Pluggy, sem precisar
                              cadastrar cada movimentação.
                            </p>
                          </div>
                          <div className="source-detail">
                            <span>Atualização na fonte</span>
                            <strong>
                              {connections.length > 1
                                ? "Consulte cada conexão"
                                : connections.length
                                  ? timestamp(
                                      connections[0].last_provider_update_at,
                                    )
                                  : "Não disponível"}
                            </strong>
                          </div>
                          <p className="fine-print">
                            Recarregar esta tela não força uma atualização no
                            banco.
                          </p>
                          <button
                            className="text-button"
                            onClick={() => setView("connections")}
                          >
                            Detalhes da conexão
                          </button>
                        </section>
                      </div>
                    </>
                  )}
                  {(view === "overview" || view === "transactions") && (
                    <Transactions
                      accounts={accounts}
                      hidden={hidden}
                      revision={revision}
                      compact={view === "overview"}
                      onExpand={() => setView("transactions")}
                    />
                  )}
                  {view === "statements" && (
                    <Statements
                      accounts={accounts}
                      hidden={hidden}
                      revision={revision}
                    />
                  )}
                </>
              )}
              {view === "connections" && (
                <Connections connections={connections} />
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}

function Overview({
  accounts,
  hidden,
  revision,
  onStatements,
  onToggleVisibility,
}: {
  accounts: Account[];
  hidden: boolean;
  revision: number;
  onStatements: () => void;
  onToggleVisibility: () => void;
}) {
  const banks = accounts.filter((account) => account.type === "BANK");
  const cards = accounts.filter((account) => account.type === "CREDIT");
  const balances = totals(
    banks,
    (account) => account.balance,
    (account) => account.currency,
  );
  const limits = totals(
    cards,
    (account) => account.available_credit_limit,
    (account) => account.currency,
  );
  return (
    <section className="summary-grid" aria-label="Resumo financeiro">
      <div className="summary-card featured">
        <div className="summary-label">
          <span>Saldo nas contas</span>
          <Wallet size={20} />
        </div>
        <div className="balance-line">
          <div className="summary-values">
            {balances.length ? (
              balances.map((item) => (
                <div key={item.currency}>
                  <Amount
                    value={item.amount}
                    currency={item.currency}
                    hidden={hidden}
                  />
                </div>
              ))
            ) : (
              <span className="unavailable">Não informado</span>
            )}
          </div>
          <button
            className="icon-button balance-visibility"
            aria-label={hidden ? "Mostrar valores" : "Ocultar valores"}
            aria-pressed={hidden}
            onClick={onToggleVisibility}
          >
            {hidden ? <EyeOff size={19} /> : <Eye size={19} />}
          </button>
        </div>
        <div className="summary-foot">
          <Landmark size={14} />
          {banks.length}{" "}
          {banks.length === 1 ? "conta bancária" : "contas bancárias"}
        </div>
        {banks.some((account) => account.balance === null) && (
          <small>Há contas com saldo não informado.</small>
        )}
      </div>
      <div className="summary-card">
        <div className="summary-label">
          <span>Crédito disponível</span>
          <CreditCard size={20} />
        </div>
        <div className="summary-values">
          {limits.length ? (
            limits.map((item) => (
              <div key={item.currency}>
                <Amount
                  value={item.amount}
                  currency={item.currency}
                  hidden={hidden}
                />
              </div>
            ))
          ) : (
            <span className="unavailable">Não informado</span>
          )}
        </div>
        <div className="summary-foot">
          {cards.length}{" "}
          {cards.length === 1 ? "cartão conectado" : "cartões conectados"}
        </div>
        {cards.some((account) => account.available_credit_limit === null) && (
          <small>Há cartões com limite não informado.</small>
        )}
      </div>
      <PayablesCard
        hidden={hidden}
        revision={revision}
        onStatements={onStatements}
      />
    </section>
  );
}

function PayablesCard({
  hidden,
  revision,
  onStatements,
}: {
  hidden: boolean;
  revision: number;
  onStatements: () => void;
}) {
  const [retry, setRetry] = useState(0);
  const data = useResource(`payables-${revision}-${retry}`, (signal) =>
    request<Payables>("/payables", signal),
  );
  return (
    <div className="summary-card payables-card">
      <div className="summary-label">
        <span>A pagar</span>
        <FileText size={20} />
      </div>
      <div className="summary-values" aria-live="polite">
        {data.loading ? (
          <span className="unavailable">Carregando…</span>
        ) : data.error ? (
          <span className="unavailable">Indisponível</span>
        ) : data.data?.totals.length ? (
          data.data.totals.map((item) => (
            <div key={item.currency}>
              <Amount
                value={item.amount}
                currency={item.currency}
                hidden={hidden}
              />
            </div>
          ))
        ) : (
          <span className="unavailable">Não informado</span>
        )}
      </div>
      <div className="summary-foot">
        {data.error ? (
          <button
            className="text-button"
            onClick={() => setRetry((value) => value + 1)}
          >
            Tentar novamente
          </button>
        ) : (
          <>
            <span title="Faturas menos pagamentos registrados, mais compras pendentes sem fatura. Valores sujeitos à atualização e à conciliação da instituição.">
              Estimativa
            </span>
            <button className="text-button" onClick={onStatements}>
              Ver faturas
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function AccountCard({
  account,
  hidden,
}: {
  account: Account;
  hidden: boolean;
}) {
  const bank = account.type === "BANK";
  return (
    <article className="account-row">
      <span className={`institution-icon ${bank ? "bank" : "card"}`}>
        {bank ? <Landmark size={23} /> : <CreditCard size={23} />}
      </span>
      <div className="account-name">
        <h3>{account.name}</h3>
        <span>
          {bank ? "Conta bancária" : "Cartão de crédito"}
          <span className="separator">·</span>
          {account.currency}
        </span>
      </div>
      <div className="account-balance">
        <strong>
          <Amount
            value={account.balance}
            currency={account.currency}
            hidden={hidden}
          />
        </strong>
        <small>{bank ? "Saldo disponível" : "Saldo informado do cartão"}</small>
      </div>
    </article>
  );
}

interface Filters {
  account: string;
  status: string;
  direction: string;
  from: string;
  to: string;
  page: number;
}
const initialFilters: Filters = {
  account: "",
  status: "",
  direction: "",
  from: "",
  to: "",
  page: 0,
};

function Transactions({
  accounts,
  hidden,
  revision,
  compact,
  onExpand,
}: {
  accounts: Account[];
  hidden: boolean;
  revision: number;
  compact: boolean;
  onExpand: () => void;
}) {
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [retry, setRetry] = useState(0);
  const size = compact ? 6 : 20;
  const invalidRange = !!(
    filters.from &&
    filters.to &&
    filters.from > filters.to
  );
  const params = new URLSearchParams({
    limit: String(size),
    offset: String(filters.page * size),
  });
  if (filters.account) params.set("account_id", filters.account);
  if (filters.status) params.set("status", filters.status);
  if (filters.direction) params.set("direction", filters.direction);
  if (filters.from) params.set("date_from", `${filters.from}T00:00:00-03:00`);
  if (filters.to) params.set("date_to", `${filters.to}T23:59:59.999999-03:00`);
  const data = useResource(
    `transactions-${params}-${revision}-${retry}-${invalidRange}`,
    (signal) =>
      invalidRange
        ? Promise.resolve({
            items: [],
            total: 0,
            limit: size,
            offset: 0,
          } as Page<Transaction>)
        : request<Page<Transaction>>(`/transactions?${params}`, signal),
  );
  const change = (field: keyof Filters, value: string) =>
    setFilters((previous) => ({ ...previous, [field]: value, page: 0 }));
  const active = Object.entries(filters).some(
    ([key, value]) => key !== "page" && value !== "",
  );
  return (
    <section className="panel transactions-panel">
      <div className="section-heading">
        <div>
          <h2>
            {compact ? "Últimas movimentações" : "Histórico de movimentações"}
          </h2>
          <p>
            {compact
              ? "O que aconteceu nas suas contas e cartões."
              : "Filtre os lançamentos para encontrar o que precisa."}
          </p>
        </div>
        {compact && (
          <button className="text-button" onClick={onExpand}>
            Ver todas
          </button>
        )}
      </div>
      {!compact && (
        <div className="filters">
          <label>
            Conta
            <select
              value={filters.account}
              onChange={(event) => change("account", event.target.value)}
            >
              <option value="">Todas as contas</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Estado
            <select
              value={filters.status}
              onChange={(event) => change("status", event.target.value)}
            >
              <option value="">Todos os estados</option>
              <option value="POSTED">Consolidado</option>
              <option value="PENDING">Pendente</option>
            </select>
          </label>
          <label>
            Tipo
            <select
              value={filters.direction}
              onChange={(event) => change("direction", event.target.value)}
            >
              <option value="">Entradas e saídas</option>
              <option value="DEBIT">Saídas</option>
              <option value="CREDIT">Entradas / créditos</option>
            </select>
          </label>
          <label>
            De
            <input
              aria-invalid={invalidRange}
              type="date"
              value={filters.from}
              onChange={(event) => change("from", event.target.value)}
            />
          </label>
          <label>
            Até
            <input
              aria-invalid={invalidRange}
              type="date"
              value={filters.to}
              onChange={(event) => change("to", event.target.value)}
            />
          </label>
          {active && (
            <button
              className="clear-filter"
              onClick={() => setFilters(initialFilters)}
            >
              Limpar filtros
            </button>
          )}
        </div>
      )}
      {invalidRange ? (
        <p className="range-error" role="alert">
          A data inicial deve ser anterior ou igual à data final.
        </p>
      ) : data.loading ? (
        <Loading />
      ) : data.error ? (
        <ErrorMessage
          message={data.error}
          retry={() => setRetry((value) => value + 1)}
        />
      ) : !data.data?.items.length ? (
        <Empty title="Nenhuma movimentação encontrada">
          {active
            ? "Experimente outro período ou ajuste os filtros."
            : "As movimentações aparecerão após a sincronização."}
        </Empty>
      ) : (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Movimentação</th>
                  <th>Conta</th>
                  <th>Data</th>
                  <th>Estado</th>
                  <th className="value-column">Valor</th>
                </tr>
              </thead>
              <tbody>
                {data.data.items.map((tx) => {
                  const account = accounts.find(
                    (account) => account.id === tx.account_id,
                  );
                  const credit = tx.direction === "CREDIT";
                  return (
                    <tr key={tx.id}>
                      <td>
                        <div className="transaction-description">
                          <span
                            className={`transaction-icon ${credit ? "incoming" : ""}`}
                          >
                            {tx.is_statement_payment ? (
                              <CreditCard size={18} />
                            ) : credit ? (
                              <ArrowDownLeft size={18} />
                            ) : (
                              <ArrowUpRight size={18} />
                            )}
                          </span>
                          <div>
                            <strong>{tx.description}</strong>
                            <small>
                              {tx.is_statement_payment
                                ? "Pagamento de fatura · não é renda"
                                : tx.installment_number && tx.total_installments
                                  ? `Parcela ${tx.installment_number} de ${tx.total_installments}`
                                  : account?.type === "CREDIT"
                                    ? credit
                                      ? "Crédito no cartão"
                                      : "Compra no cartão"
                                    : credit
                                      ? "Entrada na conta"
                                      : "Saída da conta"}
                            </small>
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className="table-account">
                          {account?.name ?? "Conta não disponível"}
                        </span>
                      </td>
                      <td className="date-cell">
                        {dateLabel(tx.occurred_at, { year: "numeric" })}
                      </td>
                      <td>
                        <span
                          className={`status ${tx.status === "PENDING" ? "amber" : "neutral"}`}
                        >
                          {tx.status === "PENDING" ? "Pendente" : "Consolidado"}
                        </span>
                      </td>
                      <td
                        className={`value-column transaction-value ${credit && !tx.is_statement_payment ? "positive" : ""}`}
                      >
                        <Amount
                          value={tx.flow_amount}
                          currency={tx.currency}
                          hidden={hidden}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {!compact && (
            <div className="pagination">
              <span>
                {data.data.offset + 1}–
                {data.data.offset + data.data.items.length} de {data.data.total}{" "}
                movimentações
              </span>
              <div>
                <button
                  className="icon-button"
                  aria-label="Página anterior"
                  disabled={filters.page === 0}
                  onClick={() =>
                    setFilters((previous) => ({
                      ...previous,
                      page: previous.page - 1,
                    }))
                  }
                >
                  <ChevronLeft size={18} />
                </button>
                <span>Página {filters.page + 1}</span>
                <button
                  className="icon-button"
                  aria-label="Próxima página"
                  disabled={data.data.offset + size >= data.data.total}
                  onClick={() =>
                    setFilters((previous) => ({
                      ...previous,
                      page: previous.page + 1,
                    }))
                  }
                >
                  <ChevronRight size={18} />
                </button>
              </div>
            </div>
          )}
          <div className="table-note">
            <CircleHelp size={14} />
            <span>
              “Consolidado” no cartão indica lançamento em fatura, não
              pagamento. Créditos no cartão não são necessariamente renda.
            </span>
          </div>
        </>
      )}
    </section>
  );
}

function Statements({
  accounts,
  hidden,
  revision,
}: {
  accounts: Account[];
  hidden: boolean;
  revision: number;
}) {
  const [account, setAccount] = useState("");
  const [page, setPage] = useState(0);
  const [retry, setRetry] = useState(0);
  const query = new URLSearchParams({ limit: "12", offset: String(page * 12) });
  if (account) query.set("account_id", account);
  const data = useResource(`bills-${query}-${revision}-${retry}`, (signal) =>
    request<Page<Statement>>(`/statements?${query}`, signal),
  );
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <h2>Faturas do cartão</h2>
          <p>Valores informados pela instituição, por vencimento.</p>
        </div>
        <label className="bill-filter">
          <span className="sr-only">Filtrar cartão</span>
          <select
            value={account}
            onChange={(event) => {
              setAccount(event.target.value);
              setPage(0);
            }}
          >
            <option value="">Todos os cartões</option>
            {accounts
              .filter((item) => item.type === "CREDIT")
              .map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
          </select>
        </label>
      </div>
      {data.loading ? (
        <Loading />
      ) : data.error ? (
        <ErrorMessage
          message={data.error}
          retry={() => setRetry((value) => value + 1)}
        />
      ) : !data.data?.items.length ? (
        <Empty title="Nenhuma fatura disponível">
          As faturas aparecem quando disponibilizadas pela instituição.
        </Empty>
      ) : (
        <>
          <div className="statement-grid">
            {data.data.items.map((bill) => (
              <article className="statement-card" key={bill.id}>
                <div className="statement-top">
                  <span className="statement-icon">
                    <FileText size={21} />
                  </span>
                  <span>Vencimento</span>
                  <strong>
                    {dateLabel(bill.due_date, { year: "numeric" })}
                  </strong>
                </div>
                <p>
                  {accounts.find((item) => item.id === bill.account_id)?.name ??
                    "Cartão"}
                </p>
                <h3>
                  <Amount
                    value={bill.total_amount}
                    currency={bill.currency}
                    hidden={hidden}
                  />
                </h3>
                <dl>
                  <div>
                    <dt>Fechamento</dt>
                    <dd>
                      {bill.closing_date
                        ? dateLabel(bill.closing_date, { year: "numeric" })
                        : "Não informado"}
                    </dd>
                  </div>
                  <div>
                    <dt>Pagamento mínimo</dt>
                    <dd>
                      <Amount
                        value={bill.minimum_payment}
                        currency={bill.currency}
                        hidden={hidden}
                      />
                    </dd>
                  </div>
                </dl>
                <div className="bill-payments">
                  <Check size={16} />
                  <span>
                    {bill.payments.length
                      ? `${bill.payments.length} pagamento(s) registrado(s)`
                      : "Sem pagamentos registrados"}
                  </span>
                </div>
                {bill.payments.length > 0 && (
                  <details>
                    <summary>Consultar pagamentos</summary>
                    <ul>
                      {bill.payments.map((payment, index) => (
                        <li key={index}>
                          <span>
                            {dateLabel(payment.payment_date, {
                              year: "numeric",
                            })}
                          </span>
                          <Amount
                            value={payment.amount}
                            currency={bill.currency}
                            hidden={hidden}
                          />
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </article>
            ))}
          </div>
          <div className="pagination">
            <span>{data.data.total} faturas disponíveis</span>
            <div>
              <button
                className="icon-button"
                aria-label="Faturas anteriores"
                disabled={page === 0}
                onClick={() => setPage((value) => value - 1)}
              >
                <ChevronLeft size={18} />
              </button>
              <span>Página {page + 1}</span>
              <button
                className="icon-button"
                aria-label="Mais faturas"
                disabled={(page + 1) * 12 >= data.data.total}
                onClick={() => setPage((value) => value + 1)}
              >
                <ChevronRight size={18} />
              </button>
            </div>
          </div>
        </>
      )}
      <div className="table-note">
        <CircleHelp size={14} />
        <span>
          Pagamentos registrados não confirmam, por si só, a quitação total. O
          saldo do cartão pode incluir valores de outras faturas.
        </span>
      </div>
    </section>
  );
}

function Connections({ connections }: { connections: Connection[] }) {
  if (!connections.length)
    return (
      <section className="panel">
        <Empty title="Nenhuma conexão encontrada">
          Execute a sincronização local para importar a conexão autorizada no
          Pluggy.
        </Empty>
      </section>
    );
  return (
    <div className="connections-grid">
      {connections.map((connection) => {
        const failed = connection.latest_execution?.status === "FAILED";
        const old = isOld(connection.last_provider_update_at);
        const expired =
          connection.consent_expires_at &&
          new Date(connection.consent_expires_at).getTime() < Date.now();
        return (
          <section className="panel connection-panel" key={connection.id}>
            <div className="section-heading">
              <div className="connection-title">
                <span className="institution-icon bank">
                  <Building2 size={24} />
                </span>
                <div>
                  <h2>{connection.institution_name ?? "Conexão bancária"}</h2>
                  <p>Integração via Pluggy</p>
                </div>
              </div>
              <span
                className={`status ${failed || expired || old || connection.provider_status === "PARTIAL_SUCCESS" ? "amber" : "green"}`}
              >
                {expired
                  ? "Consentimento expirado"
                  : failed
                    ? "Falha na consulta"
                    : old
                      ? "Dados desatualizados"
                      : connection.provider_status === "PARTIAL_SUCCESS"
                        ? "Atualização parcial"
                        : "Conectada"}
              </span>
            </div>
            <dl className="connection-details">
              <div>
                <dt>Última atualização na fonte</dt>
                <dd>{timestamp(connection.last_provider_update_at)}</dd>
              </div>
              <div>
                <dt>Última importação concluída</dt>
                <dd>{timestamp(connection.last_successful_sync_at)}</dd>
              </div>
              <div>
                <dt>Validade do consentimento</dt>
                <dd>{timestamp(connection.consent_expires_at)}</dd>
              </div>
              <div>
                <dt>Última execução</dt>
                <dd>
                  {connection.latest_execution?.status === "SUCCEEDED"
                    ? "Concluída"
                    : connection.latest_execution?.status === "RUNNING"
                      ? "Em andamento"
                      : failed
                        ? "Não concluída"
                        : "Ainda não executada"}
                </dd>
              </div>
            </dl>
            {failed && (
              <p className="connection-error">
                A última consulta falhou (
                {connection.latest_execution?.error_code ??
                  "erro não informado"}
                ). Os dados anteriores foram preservados.
              </p>
            )}
            <div className="connection-note">
              <RefreshCw size={17} />
              <p>
                O Meu Pluggy atualiza aproximadamente a cada 24 horas. A
                importação para este aplicativo é executada pelo comando local
                de sincronização.
              </p>
            </div>
          </section>
        );
      })}
    </div>
  );
}
