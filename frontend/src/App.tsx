import { useEffect, useState } from "react";

import "./App.css";
import { api } from "./api";
import type { KnowledgeEntry, Suggestion } from "./types";

export default function App() {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [selected, setSelected] = useState<KnowledgeEntry | null>(null);
  const [suggestion, setSuggestion] = useState<Suggestion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [asking, setAsking] = useState(false);

  useEffect(() => {
    api
      .listEntries()
      .then(setEntries)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function openEntry(id: string) {
    setError(null);
    setSuggestion(null);
    try {
      setSelected(await api.getEntry(id));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function askSuggestion() {
    if (!selected) return;
    setError(null);
    setSuggestion(null);
    setAsking(true);
    try {
      setSuggestion(await api.suggestForEntry(selected.id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>知识库</h1>
        <p className="count">{entries.length} 条</p>
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

        {!selected && !error && (
          <p className="muted">从左侧选择一条知识查看内容</p>
        )}

        {selected && (
          <>
            <header className="detail-header">
              <h2>{selected.title}</h2>
              <div className="meta">
                {selected.category && <span className="badge">{selected.category}</span>}
                <time>{new Date(selected.created_at).toLocaleString()}</time>
              </div>
            </header>

            <button type="button" onClick={askSuggestion} disabled={asking}>
              {asking ? "AI 正在阅读……" : "让 AI 给出整理建议"}
            </button>

            {suggestion && (
              <section className="suggestion">
                <h3>
                  建议 <span className="muted">（来自 {suggestion.provider}）</span>
                </h3>
                {suggestion.title && <p>标题：{suggestion.title}</p>}
                {suggestion.summary && <p>摘要：{suggestion.summary}</p>}
                {suggestion.category && <p>分类：{suggestion.category}</p>}
                {suggestion.keywords.length > 0 && (
                  <p>
                    关键词：
                    {suggestion.keywords.map((word) => (
                      <span className="badge" key={word}>
                        {word}
                      </span>
                    ))}
                  </p>
                )}
                <p className="muted">这只是建议，不会自动写入——确认功能在下一轮实现。</p>
              </section>
            )}

            <pre className="content">{selected.content}</pre>
          </>
        )}
      </main>
    </div>
  );
}