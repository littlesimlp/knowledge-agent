import { useEffect, useRef, useState } from "react";

import "./App.css";
import { api } from "./api";
import type { KnowledgeEntry, Suggestion } from "./types";

const ACCEPT = ".txt,.md,.markdown,.pdf";

/** 确认表单的草稿：关键词在输入框里用逗号分隔，比数组好编辑 */
interface Draft {
  title: string;
  summary: string;
  category: string;
  keywords: string;
}

function toDraft(entry: KnowledgeEntry): Draft {
  return {
    title: entry.title,
    summary: entry.summary ?? "",
    category: entry.category ?? "",
    keywords: (entry.keywords ?? []).join(", "),
  };
}

function fromSuggestion(suggestion: Suggestion, entry: KnowledgeEntry): Draft {
  return {
    title: suggestion.title ?? entry.title,
    summary: suggestion.summary ?? entry.summary ?? "",
    category: suggestion.category ?? entry.category ?? "",
    keywords: suggestion.keywords.join(", "),
  };
}

/** 逗号（中英文）或空白分隔 → 去空 → 去重 */
function parseKeywords(raw: string): string[] {
  const parts = raw
    .split(/[,，\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
  return Array.from(new Set(parts));
}

export default function App() {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [selected, setSelected] = useState<KnowledgeEntry | null>(null);
  const [suggestion, setSuggestion] = useState<Suggestion | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [saving, setSaving] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  async function refresh(preferredId?: string) {
    const list = await api.listEntries();
    setEntries(list);
    const target =
      (preferredId && list.find((item) => item.id === preferredId)) || list[0];
    setSelected(target ?? null);
    setSuggestion(null);
    setDraft(target ? toDraft(target) : null);
  }

  useEffect(() => {
    refresh()
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
    // 只在首次挂载时拉一次
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function openEntry(id: string) {
    setError(null);
    setNotice(null);
    setSuggestion(null);
    try {
      const entry = await api.getEntry(id);
      setSelected(entry);
      setDraft(toDraft(entry));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    // 立刻清空，保证再选同一个文件也能触发 onChange
    event.target.value = "";
    if (!file) return;

    setError(null);
    setNotice(null);
    setUploading(true);
    try {
      const result = await api.uploadFile(file);
      await refresh(result.entry.id);
      setNotice(
        `已导入「${result.source.source_name}」：解析出 ${result.entry.content.length} 个字符`,
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
    }
  }

  async function askSuggestion() {
    if (!selected) return;
    setError(null);
    setNotice(null);
    setSuggestion(null);
    setAsking(true);
    try {
      const result = await api.suggestForEntry(selected.id);
      setSuggestion(result);
      setDraft(fromSuggestion(result, selected));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAsking(false);
    }
  }

  async function saveDraft() {
    if (!selected || !draft) return;
    setError(null);
    setNotice(null);
    setSaving(true);
    try {
      const updated = await api.updateEntry(selected.id, {
        title: draft.title.trim() || selected.title,
        summary: draft.summary.trim() || null,
        category: draft.category.trim() || null,
        keywords: parseKeywords(draft.keywords),
      });
      setSelected(updated);
      setDraft(toDraft(updated));
      setSuggestion(null);
      setEntries((prev) =>
        prev.map((item) => (item.id === updated.id ? updated : item)),
      );
      setNotice("已保存");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  function resetDraft() {
    setSuggestion(null);
    setDraft(selected ? toDraft(selected) : null);
    setNotice(null);
    setError(null);
  }

  const dirty =
    selected !== null &&
    draft !== null &&
    (draft.title !== selected.title ||
      draft.summary !== (selected.summary ?? "") ||
      draft.category !== (selected.category ?? "") ||
      draft.keywords !== (selected.keywords ?? []).join(", "));

  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>知识库</h1>
        <p className="count">{entries.length} 条</p>

        <label className={"upload" + (uploading ? " busy" : "")}>
          {uploading ? "正在解析……" : "+ 导入文件"}
          <input
            ref={fileInput}
            type="file"
            accept={ACCEPT}
            onChange={handleUpload}
            disabled={uploading}
          />
        </label>
        <p className="hint">支持 .txt / .md / .pdf，单文件上限 5 MB</p>

        {loading && <p className="muted">加载中……</p>}
        <ul className="entry-list">
          {entries.map((entry) => (
            <li key={entry.id}>
              <button
                type="button"
                className={selected?.id === entry.id ? "active" : ""}
                onClick={() => openEntry(entry.id)}
              >
                <span className="entry-title">{entry.title}</span>
                {entry.category && (
                  <span className="badge">{entry.category}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <main className="detail">
        {error && <div className="error">{error}</div>}
        {notice && <div className="notice">{notice}</div>}

        {!selected && !error && (
          <p className="muted">从左侧选择一条知识，或导入一个文件</p>
        )}

        {selected && draft && (
          <>
            <header className="detail-header">
              <h2>{selected.title}</h2>
              <div className="meta">
                {selected.category && (
                  <span className="badge">{selected.category}</span>
                )}
                <time>{new Date(selected.created_at).toLocaleString()}</time>
              </div>
            </header>

            <div className="actions">
              <button type="button" onClick={askSuggestion} disabled={asking}>
                {asking ? "AI 正在阅读……" : "让 AI 给出整理建议"}
              </button>
              {suggestion && (
                <span className="muted">
                  建议来自 {suggestion.provider}
                  {suggestion.provider === "fake" && "（未配置真实模型）"}
                </span>
              )}
            </div>

            <section className="draft">
              <h3>确认信息</h3>
              <p className="hint">
                这些字段会被保存。AI 建议只是填充，改完点保存才生效。
              </p>

              <label className="field">
                <span>标题</span>
                <input
                  value={draft.title}
                  maxLength={200}
                  onChange={(e) =>
                    setDraft({ ...draft, title: e.target.value })
                  }
                />
              </label>

              <label className="field">
                <span>摘要</span>
                <textarea
                  rows={2}
                  value={draft.summary}
                  onChange={(e) =>
                    setDraft({ ...draft, summary: e.target.value })
                  }
                />
              </label>

              <label className="field">
                <span>分类</span>
                <input
                  value={draft.category}
                  maxLength={100}
                  onChange={(e) =>
                    setDraft({ ...draft, category: e.target.value })
                  }
                />
              </label>

              <label className="field">
                <span>关键词</span>
                <input
                  value={draft.keywords}
                  placeholder="用逗号分隔，最多 8 个"
                  onChange={(e) =>
                    setDraft({ ...draft, keywords: e.target.value })
                  }
                />
                <span className="hint">
                  将保存为 {parseKeywords(draft.keywords).length} 个
                </span>
              </label>

              <div className="actions">
                <button
                  type="button"
                  onClick={saveDraft}
                  disabled={saving || !dirty}
                >
                  {saving ? "保存中……" : "保存"}
                </button>
                <button
                  type="button"
                  className="secondary"
                  onClick={resetDraft}
                  disabled={saving || !dirty}
                >
                  放弃修改
                </button>
                {dirty && <span className="hint">有未保存的修改</span>}
              </div>
            </section>

            <h3>正文</h3>
            <pre className="content">{selected.content}</pre>
          </>
        )}
      </main>
    </div>
  );
}