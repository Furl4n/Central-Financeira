import { test, expect, type Page } from "@playwright/test";

const accounts = [
  {
    id: "bank",
    connection_id: "connection",
    type: "BANK",
    name: "Conta de teste",
    currency: "BRL",
    balance: "1234.56",
    available_credit_limit: null,
  },
  {
    id: "card",
    connection_id: "connection",
    type: "CREDIT",
    name: "Cartão de teste",
    currency: "BRL",
    balance: "840.30",
    available_credit_limit: "4159.70",
  },
];
const transactions = Array.from({ length: 25 }, (_, index) => ({
  id: `tx-${index}`,
  account_id: index % 2 ? "card" : "bank",
  description: `Movimentação fictícia ${index + 1}`,
  occurred_at: "2026-11-18T12:00:00Z",
  flow_amount: index === 0 ? "99.99" : "-45.90",
  currency: "BRL",
  direction: index === 0 ? "CREDIT" : "DEBIT",
  status: index % 2 ? "PENDING" : "POSTED",
  installment_number: index === 1 ? 2 : null,
  total_installments: index === 1 ? 5 : null,
  is_statement_payment: index === 0,
}));

async function mockAPI(
  page: Page,
  options: { error?: boolean; empty?: boolean; stale?: boolean } = {},
) {
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    if (options.error)
      return route.fulfill({
        status: 503,
        json: { detail: "Dados não devem aparecer em erro" },
      });
    if (url.pathname === "/api/payables")
      return route.fulfill({
        json: {
          totals: [{ currency: "BRL", amount: "640.30" }],
          statement_count: 1,
          pending_purchase_count: 0,
          boletos_available: false,
          estimated: true,
        },
      });
    const paginate = (items: unknown[]) => {
      const limit = Number(url.searchParams.get("limit") ?? 50);
      const offset = Number(url.searchParams.get("offset") ?? 0);
      return {
        items: items.slice(offset, offset + limit),
        total: items.length,
        limit,
        offset,
      };
    };
    if (url.pathname === "/api/accounts")
      return route.fulfill({ json: paginate(options.empty ? [] : accounts) });
    if (url.pathname === "/api/sync-status")
      return route.fulfill({
        json: options.empty
          ? []
          : [
              {
                id: "connection",
                institution_name: "Banco de teste",
                provider_status: "UPDATED",
                last_provider_update_at: options.stale
                  ? "2020-01-01T12:00:00Z"
                  : new Date().toISOString(),
                last_successful_sync_at: new Date().toISOString(),
                consent_expires_at: "2099-11-18T12:00:00Z",
                latest_execution: { status: "SUCCEEDED", error_code: null },
              },
            ],
      });
    if (url.pathname === "/api/transactions") {
      let items = [...transactions];
      if (url.searchParams.get("account_id"))
        items = items.filter(
          (tx) => tx.account_id === url.searchParams.get("account_id"),
        );
      if (url.searchParams.get("status"))
        items = items.filter(
          (tx) => tx.status === url.searchParams.get("status"),
        );
      if (url.searchParams.get("direction"))
        items = items.filter(
          (tx) => tx.direction === url.searchParams.get("direction"),
        );
      return route.fulfill({ json: paginate(items) });
    }
    if (url.pathname === "/api/statements")
      return route.fulfill({
        json: paginate([
          {
            id: "bill",
            account_id: "card",
            due_date: "2026-11-25",
            closing_date: null,
            total_amount: "840.30",
            currency: "BRL",
            minimum_payment: null,
            payments: [{ amount: "200.00", payment_date: "2026-11-20" }],
          },
        ]),
      });
    return route.fulfill({ status: 404, json: {} });
  });
}

test("separa saldo e crédito, oculta valores e não apresenta pagamento como renda", async ({
  page,
}) => {
  await mockAPI(page);
  await page.goto("/");
  const summary = page.getByRole("region", { name: "Resumo financeiro" });
  await expect(summary.getByText("R$ 1.234,56")).toBeVisible();
  await expect(summary.getByText("R$ 4.159,70")).toBeVisible();
  await expect(
    page.getByText("Pagamento de fatura · não é renda"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Ocultar valores" }).click();
  await expect(page.getByText("R$ 1.234,56")).toHaveCount(0);
  await expect(summary.getByText("••••••")).toHaveCount(3);
  await page.getByRole("button", { name: "Mostrar valores" }).click();
  await expect(summary.getByText("R$ 1.234,56")).toBeVisible();
});

test("pagina e reinicia a paginação ao filtrar, enviando o fuso de Brasília", async ({
  page,
}) => {
  await mockAPI(page);
  await page.goto("/");
  await page
    .getByRole("button", { name: "Movimentações", exact: true })
    .click();
  await expect(page.getByText("1–20 de 25 movimentações")).toBeVisible();
  await page.getByRole("button", { name: "Próxima página" }).click();
  await expect(page.getByText("21–25 de 25 movimentações")).toBeVisible();
  await page
    .getByRole("combobox", { name: "Conta", exact: true })
    .selectOption("card");
  await expect(page.getByText("1–12 de 12 movimentações")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Página anterior" }),
  ).toBeDisabled();
  await page
    .getByRole("combobox", { name: "Estado", exact: true })
    .selectOption("PENDING");
  await expect(page.getByText("Parcela 2 de 5")).toBeVisible();
  const sent = page.waitForRequest((request) =>
    new URL(request.url()).searchParams.has("date_from"),
  );
  await page.getByLabel("De", { exact: true }).fill("2026-11-01");
  expect(new URL((await sent).url()).searchParams.get("date_from")).toBe(
    "2026-11-01T00:00:00-03:00",
  );
  await page.getByLabel("Até", { exact: true }).fill("2026-10-01");
  await expect(page.getByRole("alert")).toContainText(
    "A data inicial deve ser anterior",
  );
  await page.getByRole("button", { name: "Limpar filtros" }).click();
  await expect(page.getByText("1–20 de 25 movimentações")).toBeVisible();
});

test("fatura conserva o dia do vencimento e permite consultar pagamentos", async ({
  page,
}) => {
  await mockAPI(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Faturas", exact: true }).click();
  await expect(page.getByRole("heading", { name: "R$ 840,30" })).toBeVisible();
  await expect(page.getByText(/25 de nov/)).toBeVisible();
  await page.getByText("Consultar pagamentos", { exact: true }).click();
  await expect(page.getByText("R$ 200,00")).toBeVisible();
  await expect(page.getByText(/não confirmam, por si só/)).toBeVisible();
});

test("avisa sobre dados antigos e diferencia atualização e importação", async ({
  page,
}) => {
  await mockAPI(page, { stale: true });
  await page.goto("/");
  await expect(page.getByText(/podem estar desatualizados/)).toBeVisible();
  await page.getByRole("button", { name: "Ver conexão", exact: true }).click();
  await expect(
    page.getByText("Última atualização na fonte", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Última importação concluída")).toBeVisible();
});

test("mostra falha sem inventar valores e permite tentar novamente", async ({
  page,
}) => {
  await mockAPI(page, { error: true });
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText(
    "Não foi possível carregar",
  );
  await expect(page.getByText("R$ 0,00")).toHaveCount(0);
  await page.unroute("**/api/**");
  await mockAPI(page);
  await page.getByRole("button", { name: "Tentar novamente" }).click();
  await expect(page.getByText("Suas contas", { exact: true })).toBeVisible();
});

test("tela vazia e navegação sem rolagem horizontal da página", async ({
  page,
}) => {
  await mockAPI(page, { empty: true });
  await page.goto("/");
  await expect(page.getByText("Seu ponto de partida está aqui")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: /Conexões/ }).click();
  await expect(page.getByText("Nenhuma conexão encontrada")).toBeVisible();
});

test("layout preenchido cabe na tela e não envia dados para serviços externos", async ({
  page,
}, testInfo) => {
  const external: string[] = [];
  page.on("request", (request) => {
    if (!request.url().startsWith("http://127.0.0.1:"))
      external.push(request.url());
  });
  await mockAPI(page);
  await page.goto("/");
  await expect(page.getByText("Suas contas", { exact: true })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("dashboard.png"),
    fullPage: true,
  });
  expect(external).toEqual([]);
});

test("cartão A pagar substitui conexões e abre as faturas sem aviso de boletos", async ({ page }) => {
  await mockAPI(page);
  await page.goto('/');
  const summary = page.getByRole('region', { name: 'Resumo financeiro' });
  await expect(summary.getByText('A pagar', { exact: true })).toBeVisible();
  await expect(summary.getByText('R$ 640,30')).toBeVisible();
  await expect(summary.getByText('Conexões bancárias')).toHaveCount(0);
  await expect(summary.getByText(/boletos/i)).toHaveCount(0);
  await summary.getByRole('button', { name: 'Ver faturas' }).click();
  await expect(page.getByRole('heading', { name: 'Faturas do cartão' })).toBeVisible();
});
