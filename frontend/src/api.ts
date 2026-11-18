import { useEffect, useState } from "react";
import type { Page } from "./types";

export async function request<T>(
  path: string,
  signal: AbortSignal,
): Promise<T> {
  const response = await fetch(`/api${path}`, { signal, cache: "no-store" });
  if (!response.ok)
    throw new Error(
      "Confira se o backend e o banco estão em execução e tente novamente.",
    );
  return response.json() as Promise<T>;
}

export async function allPages<T>(
  path: string,
  signal: AbortSignal,
): Promise<T[]> {
  const result: T[] = [];
  for (let offset = 0; offset < 100_000; offset += 200) {
    const page = await request<Page<T>>(
      `${path}?limit=200&offset=${offset}`,
      signal,
    );
    if (!Array.isArray(page.items))
      throw new Error("A API retornou um formato inesperado.");
    result.push(...page.items);
    if (result.length >= page.total) return result;
    if (page.items.length === 0)
      throw new Error("Consulta incompleta. Recarregue os dados.");
  }
  throw new Error("A consulta excedeu o limite de registros desta tela.");
}

export function useResource<T>(
  key: string,
  load: (signal: AbortSignal) => Promise<T>,
) {
  const [state, setState] = useState<{
    key: string;
    data?: T;
    error?: string;
    loading: boolean;
  }>({ key, loading: true });
  useEffect(() => {
    const controller = new AbortController();
    setState({ key, loading: true });
    load(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ key, data, loading: false });
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setState({
            key,
            error:
              error instanceof Error ? error.message : "Falha na consulta.",
            loading: false,
          });
      });
    return () => controller.abort();
    // The key represents every input to the request; cleanup prevents stale results.
  }, [key]);
  return state.key === key
    ? state
    : { key, loading: true, data: undefined, error: undefined };
}
