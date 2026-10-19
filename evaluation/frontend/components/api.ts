import type { DashboardData } from "../types/observatory";

const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";

export async function getDashboard(from?: string, to?: string): Promise<DashboardData> {
  const query = new URLSearchParams();
  if (from) query.set("date_from", from);
  if (to) query.set("date_to", to);
  const response = await fetch(`${apiBase}/dashboard${query.size ? `?${query}` : ""}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    let detail = `The observability API returned ${response.status}.`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Retain the safe, status-based error above.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<DashboardData>;
}
