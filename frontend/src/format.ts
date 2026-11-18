import Decimal from "decimal.js";

export function money(value: string | null, currency = "BRL") {
  if (value === null) return "Não informado";
  const decimal = new Decimal(value).toDecimalPlaces(2, Decimal.ROUND_HALF_UP);
  const [whole, fraction] = decimal.abs().toFixed(2).split(".");
  return `${decimal.isNegative() ? "−" : ""}${currency === "BRL" ? "R$" : currency} ${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ".")},${fraction}`;
}

export function totals<T>(
  items: T[],
  amount: (item: T) => string | null,
  currency: (item: T) => string,
) {
  const grouped = new Map<string, Decimal>();
  for (const item of items) {
    const value = amount(item);
    if (value !== null)
      grouped.set(
        currency(item),
        (grouped.get(currency(item)) ?? new Decimal(0)).plus(value),
      );
  }
  return [...grouped.entries()].map(([currency, amount]) => ({
    currency,
    amount: amount.toFixed(),
  }));
}

export function dateLabel(value: string, options?: Intl.DateTimeFormatOptions) {
  const date = new Date(
    value.length === 10 ? `${value}T12:00:00-03:00` : value,
  );
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Sao_Paulo",
    day: "2-digit",
    month: "short",
    ...options,
  }).format(date);
}

export function timestamp(value: string | null) {
  return value
    ? dateLabel(value, { year: "numeric", hour: "2-digit", minute: "2-digit" })
    : "Ainda não disponível";
}

export function isOld(value: string | null) {
  return !value || Date.now() - new Date(value).getTime() > 36 * 60 * 60 * 1000;
}
