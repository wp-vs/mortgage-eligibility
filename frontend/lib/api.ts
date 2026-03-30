const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiRequest(path: string, options?: RequestInit) {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "API request failed");
  }
  return res.json();
}

export async function createCustomer(): Promise<{ id: number }> {
  return apiRequest("/api/customers/", { method: "POST" });
}

export async function getCustomer(id: number) {
  return apiRequest(`/api/customers/${id}`);
}

export async function sendMessage(customerId: number, message: string) {
  return apiRequest("/api/chat/send", {
    method: "POST",
    body: JSON.stringify({ customer_id: customerId, message }),
  });
}

export function streamMessage(customerId: number, message: string) {
  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  return fetch(`${API}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ customer_id: customerId, message }),
  });
}

export async function getConversationHistory(customerId: number) {
  return apiRequest(`/api/chat/${customerId}/history`);
}

export async function initiateBanking(customerId: number) {
  return apiRequest("/api/banking/connect", {
    method: "POST",
    body: JSON.stringify({ customer_id: customerId }),
  });
}

export async function bankingCallback(code: string, connectionId: number) {
  return apiRequest("/api/banking/callback", {
    method: "POST",
    body: JSON.stringify({ code, connection_id: connectionId }),
  });
}

export async function getBankingStatus(customerId: number) {
  return apiRequest(`/api/banking/${customerId}/status`);
}

export async function getBankingAnalysis(customerId: number) {
  return apiRequest(`/api/banking/${customerId}/analysis`);
}

export async function matchProducts(customerId: number) {
  return apiRequest(`/api/products/${customerId}/match`, { method: "POST" });
}

export async function getRecommendations(customerId: number) {
  return apiRequest(`/api/products/${customerId}/recommendations`);
}

export async function brokerLogin(email: string, password: string) {
  return apiRequest("/api/broker/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getBrokerCases() {
  return apiRequest("/api/broker/cases");
}

export async function getBrokerCaseDetail(customerId: number) {
  return apiRequest(`/api/broker/cases/${customerId}`);
}

export async function reviewRecommendation(
  customerId: number,
  recId: number,
  approved: boolean,
  notes?: string
) {
  return apiRequest(
    `/api/broker/cases/${customerId}/recommendations/${recId}/review`,
    {
      method: "POST",
      body: JSON.stringify({ approved, notes }),
    }
  );
}
