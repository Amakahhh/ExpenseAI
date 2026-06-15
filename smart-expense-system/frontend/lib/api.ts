// All requests go through the Next.js rewrite at /backend/* so the browser
// never contacts Render directly — no CORS needed.
const BASE_URL = "/backend";

// Thrown when the uploaded PDF is password-protected and no (or wrong) password was given.
export class PDFPasswordError extends Error {
  constructor() {
    super("PDF_NEEDS_PASSWORD");
    this.name = "PDFPasswordError";
  }
}

// ─── Auth token helpers ───────────────────────────────────────────────────────

export function getToken(): string | null {
  try { return localStorage.getItem("auth_token"); } catch { return null; }
}

export function setToken(token: string, email: string, name: string): void {
  localStorage.setItem("auth_token", token);
  localStorage.setItem("auth_email", email);
  localStorage.setItem("auth_name", name);
}

export function clearToken(): void {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("auth_email");
  localStorage.removeItem("auth_name");
}

export function getAuthUser(): { email: string; name: string } | null {
  try {
    const email = localStorage.getItem("auth_email");
    const name = localStorage.getItem("auth_name");
    return email ? { email, name: name ?? email } : null;
  } catch { return null; }
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ─── Auth API calls ───────────────────────────────────────────────────────────

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_email: string;
  user_name: string;
}

export async function signup(full_name: string, email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${BASE_URL}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ full_name, email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as any).detail || "Signup failed.");
  }
  return res.json();
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as any).detail || "Login failed.");
  }
  return res.json();
}

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

export interface SessionRecord {
  session_id: string;
  filename: string;
  upload_date: string;
  total_transactions: number;
  total_spend: number;
  total_income: number;
  date_range_start: string | null;
  date_range_end: string | null;
  top_category: string | null;
}

export interface SessionComparison {
  session_id: string;
  total_spend: number;
  by_category: { category: string; total: number }[];
}

// ─── API Functions ───────────────────────────────────────────────────────────

export async function uploadFile(file: File, pdfPassword?: string): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  if (pdfPassword) form.append("pdf_password", pdfPassword);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 180_000); // 3 min — covers Render cold start

  try {
    const res = await fetch(`${BASE_URL}/upload`, {
      method: "POST",
      headers: authHeaders(),
      body: form,
      signal: controller.signal,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const detail = (err as any).detail;
      if (res.status === 422 && detail === "PDF_NEEDS_PASSWORD") {
        throw new PDFPasswordError();
      }
      throw new Error(detail || "Upload failed.");
    }
    return res.json();
  } catch (err: any) {
    if (err.name === "AbortError") {
      throw new Error("Server took too long to respond. It may still be waking up. Please try again.");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

export async function getAnalytics(sessionId?: string): Promise<Analytics> {
  const url = sessionId
    ? `${BASE_URL}/analytics?session_id=${encodeURIComponent(sessionId)}`
    : `${BASE_URL}/analytics`;
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to fetch analytics.");
  return res.json();
}

export async function getTransactions(sessionId?: string): Promise<Transaction[]> {
  const url = sessionId
    ? `${BASE_URL}/transactions?session_id=${encodeURIComponent(sessionId)}`
    : `${BASE_URL}/transactions`;
  const res = await fetch(url, { headers: authHeaders() });
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
    headers: { "Content-Type": "application/json", ...authHeaders() },
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
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ description }),
  });
  if (!res.ok) throw new Error("Failed to classify.");
  return res.json();
}

export async function getSessionHistory(sessionIds?: string[]): Promise<SessionRecord[]> {
  const url = sessionIds && sessionIds.length > 0
    ? `${BASE_URL}/history?session_ids=${encodeURIComponent(sessionIds.join(","))}`
    : `${BASE_URL}/history`;
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to fetch session history.");
  const data = await res.json();
  return data.sessions ?? [];
}

export async function compareSessionSpending(sessionIds: string[]): Promise<SessionComparison[]> {
  if (sessionIds.length === 0) return [];
  const ids = sessionIds.join(",");
  const res = await fetch(`${BASE_URL}/history/compare?session_ids=${encodeURIComponent(ids)}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to compare sessions.");
  const data = await res.json();
  return data.sessions ?? [];
}

// ─── Local session store (localStorage) ─────────────────────────────────────

const LS_KEY = "expense_sessions";

export interface StoredSession {
  session_id: string;
  filename: string;
  upload_date: string;
  total_transactions: number;
  total_spend: number;
}

export function loadStoredSessions(): StoredSession[] {
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveStoredSession(session: StoredSession): void {
  const existing = loadStoredSessions().filter((s) => s.session_id !== session.session_id);
  const updated = [session, ...existing].slice(0, 10); // keep latest 10
  localStorage.setItem(LS_KEY, JSON.stringify(updated));
}

export function getActiveSessionId(): string | null {
  try {
    return localStorage.getItem("active_session_id");
  } catch {
    return null;
  }
}

export function setActiveSessionId(id: string): void {
  localStorage.setItem("active_session_id", id);
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

export function formatNaira(amount: number): string {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    minimumFractionDigits: 2,
  }).format(amount);
}
