/**
 * Cliente da API do backend (contracts/api-conventions.md): rotas com barra final,
 * versionamento via header Accept e Bearer token da sessão Supabase.
 */
import { supabase } from "./supabase";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const API_VERSION = "1";

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(`API error ${status}`);
  }
}

async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return {
    Accept: `application/json; version=${API_VERSION}`,
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: await authHeaders(),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    throw new ApiError(
      response.status,
      await response.json().catch(() => null),
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

/** PATCH multipart/form-data — usado para upload de arquivo (ex.: avatar), onde o
 * Content-Type (com boundary) deve ser definido pelo fetch, não fixado em JSON. */
async function patchForm<T>(path: string, form: FormData): Promise<T> {
  const headers = await authHeaders();
  delete headers["Content-Type"];
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers,
    body: form,
  });
  if (!response.ok) {
    throw new ApiError(response.status, await response.json().catch(() => null));
  }
  return response.json();
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
  patchForm,
  delete: <T>(path: string) => request<T>("DELETE", path),
};

/** Formato de toda listagem paginada por cursor da API. */
export interface Paginated<T> {
  next: string | null;
  previous: string | null;
  results: T[];
}
