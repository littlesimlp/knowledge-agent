import type {
  EntryPatch,
  ImportResult,
  KnowledgeEntry,
  Suggestion,
} from "./types";

/**
 * 所有请求都用相对路径。
 * 开发时由 Vite proxy 转发到后端；生产时前后端同源，代码不用改。
 */
const BASE = "";

/** 统一的失败处理：后端把用户可读说明放在 detail 里，优先展示它。 */
async function ensureOk(response: Response): Promise<void> {
  if (response.ok) return;

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  await ensureOk(response);

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

  updateEntry: (id: string, patch: EntryPatch) =>
    request<KnowledgeEntry>(`/api/entries/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),

  deleteEntry: (id: string) =>
    request<void>(`/api/entries/${id}`, { method: "DELETE" }),

  /**
   * 上传文件。
   *
   * 注意：**不要**手动设置 Content-Type。multipart 的
   * `boundary` 由浏览器生成，手动设会导致后端解析失败。
   */
  uploadFile: async (file: File, title?: string): Promise<ImportResult> => {
    const form = new FormData();
    form.append("file", file);
    if (title) {
      form.append("title", title);
    }

    const response = await fetch(`${BASE}/api/imports/file`, {
      method: "POST",
      body: form,
    });
    await ensureOk(response);
    return (await response.json()) as ImportResult;
  },
};