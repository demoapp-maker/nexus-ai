import { proxyBackend } from "@/lib/backend";

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  try {
    const upstream = await proxyBackend("/health");
    return new Response(await upstream.text(), {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return Response.json({ status: "offline" }, { status: 503 });
  }
}
