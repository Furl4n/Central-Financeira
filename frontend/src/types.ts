export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Payables {
  totals: { currency: string; amount: string }[];
  statement_count: number;
  pending_purchase_count: number;
  boletos_available: boolean;
  estimated: boolean;
}
export interface Account {
  id: string;
  connection_id: string;
  type: "BANK" | "CREDIT";
  name: string;
  currency: string;
  balance: string | null;
  available_credit_limit: string | null;
}
export interface Transaction {
  id: string;
  account_id: string;
  description: string;
  occurred_at: string;
  flow_amount: string;
  direction: "DEBIT" | "CREDIT";
  currency: string;
  status: "PENDING" | "POSTED";
  installment_number: number | null;
  total_installments: number | null;
  is_statement_payment: boolean;
}
export interface Statement {
  id: string;
  account_id: string;
  due_date: string;
  closing_date: string | null;
  total_amount: string;
  currency: string;
  minimum_payment: string | null;
  payments: { amount: string; payment_date: string }[];
}
export interface Connection {
  id: string;
  institution_name: string | null;
  provider_status: string | null;
  last_provider_update_at: string | null;
  consent_expires_at: string | null;
  last_successful_sync_at: string | null;
  latest_execution: { status: string; error_code: string | null } | null;
}
