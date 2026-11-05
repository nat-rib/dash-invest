/** Cliente HTTP mínimo: repassa erros do backend como mensagens acionáveis. */

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function handle(response: Response): Promise<Response> {
  if (response.ok) return response;
  let message = `Erro HTTP ${response.status}`;
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (payload && typeof payload.detail === "string") message = payload.detail;
  } catch {
    /* resposta sem corpo JSON */
  }
  throw new ApiError(response.status, message);
}

export function getJson<T>(url: string): Promise<T> {
  return fetch(url).then(handle).then((response) => response.json() as T);
}

export function sendJson<T>(url: string, method: string, body: unknown): Promise<T> {
  return fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? null),
  })
    .then(handle)
    .then((response) => response.json() as T);
}

export function sendForm<T>(url: string, file: File, fields: Record<string, string>): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  for (const [key, value] of Object.entries(fields)) form.append(key, value);
  return fetch(url, { method: "POST", body: form })
    .then(handle)
    .then((response) => response.json() as T);
}
