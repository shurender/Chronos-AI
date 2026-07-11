export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, '') || 'http://localhost:8000';

export class ChronosApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = 'ChronosApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function parseResponseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function getErrorMessage(status: number, body: unknown): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (detail && typeof detail === 'object') {
      const parts = [
        ...(((detail as { errors?: unknown }).errors as string[] | undefined) ?? []),
        ...(((detail as { warnings?: unknown }).warnings as string[] | undefined) ?? []),
      ].filter((item): item is string => typeof item === 'string' && item.trim().length > 0);
      if (parts.length) return parts.join(' ');
    }
    return JSON.stringify(detail);
  }
  if (typeof body === 'string' && body.trim()) return body;
  return `Chronos API request failed with status ${status}`;
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  const isFormData = init.body instanceof FormData;

  if (!headers.has('Accept')) headers.set('Accept', 'application/json');
  if (!isFormData && init.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
    });
  } catch (error) {
    const reason = error instanceof Error && error.message ? ` (${error.message})` : '';
    throw new ChronosApiError(
      0,
      `Could not reach the Chronos API at ${API_BASE_URL}. Start the backend and verify VITE_API_BASE_URL and CORS_ORIGINS.${reason}`,
      error,
    );
  }
  const body = await parseResponseBody(response);

  if (!response.ok) {
    throw new ChronosApiError(response.status, getErrorMessage(response.status, body), body);
  }

  return body as T;
}
