const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface Transaction {
  id: number;
  date: string;
  description: string;
  amount: number;
  transaction_type: "debit" | "credit";
  predicted_category: string;
  confidence: number;
  is_corrected: boolean;
  corrected_category: string | null;
}

export interface UploadResponse {
  session_id: string;
  total: number;
  transactions: Transaction[];
}

export interface CategoryStat {
  category: string;
  total: number;
  count: number;
}

export interface MonthlyStat {
  month: string;
  total: number;
}

export interface MerchantStat {
  merchant: string;
  total: number;
  count: number;
  category: string;
}

export interface Analytics {
  by_category: CategoryStat[];
  by_month: MonthlyStat[];
  top_merchants: MerchantStat[];
  total_spend: number;
  total_income: number;
  transaction_count: number;
  income_count: number;
  total_count: number;
}

// ─── API Functions ───────────────────────────────────────────────────────────

export async function uploadFile(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE_URL}/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as any).detail || "Upload failed.");
  }
  return res.json();
}

export async function getAnalytics(sessionId?: string): Promise<Analytics> {
  const url = sessionId
    ? `${BASE_URL}/analytics?session_id=${encodeURIComponent(sessionId)}`
    : `${BASE_URL}/analytics`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch analytics.");
  return res.json();
}

export async function getTransactions(sessionId?: string): Promise<Transaction[]> {
  const url = sessionId
    ? `${BASE_URL}/transactions?session_id=${encodeURIComponent(sessionId)}`
    : `${BASE_URL}/transactions`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch transactions.");
  const data = await res.json();
  return data.transactions ?? [];
}

export async function correctTransaction(
  transactionId: number,
  correctCategory: string,
): Promise<{ success: boolean }> {
  const res = await fetch(`${BASE_URL}/correct`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transaction_id: transactionId, correct_category: correctCategory }),
  });
  if (!res.ok) throw new Error("Failed to correct transaction.");
  return res.json();
}

export async function classifySingle(
  description: string,
): Promise<{ category: string; confidence: number }> {
  const res = await fetch(`${BASE_URL}/categorize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description }),
  });
  if (!res.ok) throw new Error("Failed to classify.");
  return res.json();
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

export function formatNaira(amount: number): string {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    minimumFractionDigits: 2,
  }).format(amount);
}
