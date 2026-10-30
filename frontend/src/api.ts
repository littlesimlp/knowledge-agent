import type { KnowledgeEntry, Suggestion } from "./types";

/**
 * 所有请求都用相对路径。
 * 开发时由 Vite proxy 转发到后端；生产时前后端同源，代码不用改。
 */
const BASE = "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    // 后端把用户可读的说明放在 detail 里，优先展示它
    let detail = `请求失败（HTTP ${response.status}）`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // 响应不是 JSON，保留默认说明
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  listEntries: () => request<KnowledgeEntry[]>("/api/entries"),

  getEntry: (id: string) => request<KnowledgeEntry>(`/api/entries/${id}`),

  suggestForEntry: (id: string) =>
    request<Suggestion>(`/api/entries/${id}/suggestions`, { method: "POST" }),

  updateEntry: (id: string, patch: Partial<KnowledgeEntry>) =>
    request<KnowledgeEntry>(`/api/entries/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),

  deleteEntry: (id: string) =>
    request<void>(`/api/entries/${id}`, { method: "DELETE" }),
};