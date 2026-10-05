const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function proxyBackend(path: string, init?: RequestInit): Promise<Response> {
  return fetch(`${backendUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
}
