import { useEffect, useRef, useState } from "react";

import "./App.css";
import { api } from "./api";
import type {
  AskResponse,
  KnowledgeEntry,
  KnowledgeSource,
  KnowledgeSourceDetail,
  LLMSettings,
  LLMSettingsUpdate,
  Suggestion,
} from "./types";

const ACCEPT = ".txt,.md,.markdown,.pdf";

/** 确认表单的草稿：关键词在输入框里用逗号分隔，比数组好编辑 */
interface Draft {
  title: string;
  summary: string;
  category: string;
  keywords: string;
}

/** 设置弹窗的草稿；api_key 留空表示不修改 */
interface SettingsForm {
  provider: string;
  base_url: string;
  model: string;
  api_key: string;
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
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [viewingSource, setViewingSource] =
    useState<KnowledgeSourceDetail | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [question, setQuestion] = useState("");
  const [askingQuestion, setAskingQuestion] = useState(false);
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settings, setSettings] = useState<LLMSettings | null>(null);
  const [settingsForm, setSettingsForm] = useState<SettingsForm>({
    provider: "fake",
    base_url: "",
    model: "",
    api_key: "",
  });
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsTesting, setSettingsTesting] = useState(false);
  const [settingsMessage, setSettingsMessage] = useState<string | null>(null);
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

  // 切换条目时重新拉来源。依赖用 id 而不是对象：保存后 setSelected 会换对象，
  // 但来源没变，不该重复请求。
  useEffect(() => {
    const entryId = selected?.id;
    if (!entryId) {
      setSources([]);
      return;
    }

    let cancelled = false;
    // 先清空，避免加载期间短暂显示上一条条目的来源
    setSources([]);
    api
      .listEntrySources(entryId)
      .then((list) => {
        if (!cancelled) setSources(list);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      });

    return () => {
      cancelled = true;
    };
  }, [selected?.id]);

  // 换条目就撤销"待确认删除"，避免把确认状态带到别的条目上
  useEffect(() => {
    setConfirmDelete(false);
  }, [selected?.id]);

  // Esc 关闭原文弹窗
  // Esc 关闭原文 / 设置弹窗
  useEffect(() => {
    if (!viewingSource && !settingsOpen) return;

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setViewingSource(null);
        setSettingsOpen(false);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [viewingSource, settingsOpen]);

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

  async function openSource(sourceId: string) {
    setError(null);
    try {
      setViewingSource(await api.getSource(sourceId));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function handleDelete() {
    if (!selected) return;

    // 第一次点击只进入确认态，第二次点击才真正删除（D-020 的二次确认）
    if (!confirmDelete) {
      setConfirmDelete(true);
      setNotice(null);
      return;
    }

    const title = selected.title;
    setError(null);
    setNotice(null);
    setDeleting(true);
    try {
      await api.deleteEntry(selected.id);
      setConfirmDelete(false);
      setViewingSource(null);
      setAnswer(null);
      await refresh();
      setNotice(`已删除「${title}」，无其它引用的来源与原文一并清理`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeleting(false);
    }
  }

    async function handleAsk() {
    const trimmed = question.trim();
    if (!trimmed) return;

    setError(null);
    setNotice(null);
    setAskingQuestion(true);
    try {
      setAnswer(await api.ask(trimmed));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAskingQuestion(false);
    }
  }

    async function openSettings() {
    setViewingSource(null);
    setSettingsOpen(true);
    setSettingsLoading(true);
    setSettingsMessage(null);
    try {
      const data = await api.getLlmSettings();
      setSettings(data);
      setSettingsForm({
        provider: data.provider,
        base_url: data.base_url,
        model: data.model,
        api_key: "",
      });
    } catch (e) {
      setSettingsMessage(`读取失败：${(e as Error).message}`);
    } finally {
      setSettingsLoading(false);
    }
  }

  async function persistSettings(clearKey = false) {
    const payload: LLMSettingsUpdate = {
      provider: settingsForm.provider,
      base_url: settingsForm.base_url,
      model: settingsForm.model,
    };
    if (clearKey) {
      payload.clear_api_key = true;
    } else if (settingsForm.api_key.trim()) {
      payload.api_key = settingsForm.api_key.trim();
    }

    const data = await api.saveLlmSettings(payload);
    setSettings(data);
    setSettingsForm({
      provider: data.provider,
      base_url: data.base_url,
      model: data.model,
      api_key: "",
    });
    return data;
  }

  async function saveSettings() {
    setSettingsSaving(true);
    setSettingsMessage(null);
    try {
      await persistSettings();
      setSettingsMessage("已保存，立即生效");
    } catch (e) {
      setSettingsMessage(`保存失败：${(e as Error).message}`);
    } finally {
      setSettingsSaving(false);
    }
  }

  async function testSettings() {
    setSettingsTesting(true);
    setSettingsMessage(null);
    try {
      // 先保存，再测试，避免"改了没保存却以为在测新配置"
      await persistSettings();
      const result = await api.testLlmSettings();
      setSettingsMessage(`连接成功（${result.provider}）`);
    } catch (e) {
      setSettingsMessage(`连接失败：${(e as Error).message}`);
    } finally {
      setSettingsTesting(false);
    }
  }

  async function clearApiKey() {
    setSettingsSaving(true);
    setSettingsMessage(null);
    try {
      await persistSettings(true);
      setSettingsMessage("已清除密钥");
    } catch (e) {
      setSettingsMessage(`清除失败：${(e as Error).message}`);
    } finally {
      setSettingsSaving(false);
    }
  }

  async function resetSettings() {
    setSettingsSaving(true);
    setSettingsMessage(null);
    try {
      await api.resetLlmSettings();
      await openSettings();
      setSettingsMessage("已恢复 .env 配置");
    } catch (e) {
      setSettingsMessage(`恢复失败：${(e as Error).message}`);
    } finally {
      setSettingsSaving(false);
    }
  }

  const canSubmitSettings =
    settingsForm.provider === "fake" || settingsForm.model.trim().length > 0;

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
        <div className="sidebar-head">
          <h1>知识库</h1>
          <button type="button" className="link-button" onClick={openSettings}>
            设置
          </button>
        </div>
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
        <section className="ask-box">
          <form
            className="ask-form"
            onSubmit={(event) => {
              event.preventDefault();
              void handleAsk();
            }}
          >
            <input
              value={question}
              maxLength={500}
              placeholder="问知识库，例如：Docker 数据卷和绑定挂载的区别？"
              onChange={(event) => setQuestion(event.target.value)}
              disabled={askingQuestion}
            />
            <button
              type="submit"
              disabled={askingQuestion || !question.trim()}
            >
              {askingQuestion ? "检索中……" : "提问"}
            </button>
          </form>

          {answer && (
            <div className={answer.grounded ? "answer" : "answer ungrounded"}>
              <p className="answer-text">{answer.answer}</p>

              {answer.citations.length > 0 && (
                <div className="citations">
                  <span className="muted">依据：</span>
                  {answer.citations.map((citation) => (
                    <button
                      key={citation.entry_id}
                      type="button"
                      className="citation"
                      title={citation.snippet}
                      onClick={() => void openEntry(citation.entry_id)}
                    >
                      {citation.title}
                    </button>
                  ))}
                </div>
              )}

              {answer.grounded ? (
                <p className="hint">
                  回答来自 {answer.provider}
                  {answer.provider === "fake" && "（未配置真实模型）"}
                </p>
              ) : (
                <p className="hint">
                  {answer.reason === "no_results"
                    ? "知识库里还没有相关内容，可以导入资料后再问。"
                    : "为避免展示没有依据的回答，这次不显示模型输出。"}
                </p>
              )}
            </div>
          )}
        </section>
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
              <button
                type="button"
                className="danger"
                onClick={handleDelete}
                disabled={deleting || saving}
              >
                {deleting ? "删除中……" : confirmDelete ? "确认删除？" : "删除"}
              </button>
              {confirmDelete && (
                <>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => setConfirmDelete(false)}
                    disabled={deleting}
                  >
                    取消
                  </button>
                  <span className="hint">条目、来源与原文一并清除，不可恢复</span>
                </>
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

            <section className="sources">
              <h3>来源（{sources.length}）</h3>
              {sources.length === 0 ? (
                <p className="muted">这条条目没有关联来源</p>
              ) : (
                <ul>
                  {sources.map((source) => (
                    <li key={source.id}>
                      <span className="source-name">{source.source_name}</span>
                      <span className="badge">{source.source_type}</span>
                      {source.source_url && (
                        <a
                          href={source.source_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          原始链接
                        </a>
                      )}
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => openSource(source.id)}
                      >
                        查看原文
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </main>

      {viewingSource && (
        <div className="modal-backdrop" onClick={() => setViewingSource(null)}>
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label={`来源原文：${viewingSource.source_name}`}
            onClick={(event) => event.stopPropagation()}
          >
            <header className="modal-header">
              <div>
                <h2>{viewingSource.source_name}</h2>
                <p className="hint">
                  {viewingSource.source_type} ·{" "}
                  {new Date(viewingSource.created_at).toLocaleString()}
                </p>
              </div>
              <button
                type="button"
                className="secondary"
                onClick={() => setViewingSource(null)}
              >
                关闭
              </button>
            </header>
            <pre className="content modal-content">
              {viewingSource.extracted_text ?? "这条来源没有保存原文。"}
            </pre>
          </div>
        </div>
      )}

            {settingsOpen && (
        <div className="modal-backdrop" onClick={() => setSettingsOpen(false)}>
          <div
            className="modal settings-modal"
            role="dialog"
            aria-modal="true"
            aria-label="AI 设置"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="modal-header">
              <div>
                <h2>AI 设置</h2>
                <p className="hint">
                  保存在 backend/data/llm.json，不进数据库，也不进备份
                </p>
              </div>
              <button
                type="button"
                className="secondary"
                onClick={() => setSettingsOpen(false)}
              >
                关闭
              </button>
            </header>

            {settingsLoading ? (
              <p className="muted">加载中……</p>
            ) : (
              <>
                <label className="field">
                  <span>Provider</span>
                  <select
                    value={settingsForm.provider}
                    onChange={(event) =>
                      setSettingsForm({
                        ...settingsForm,
                        provider: event.target.value,
                      })
                    }
                  >
                    <option value="fake">fake（不联网）</option>
                    <option value="deepseek">deepseek</option>
                    <option value="siliconflow">siliconflow</option>
                  </select>
                </label>

                <label className="field">
                  <span>Model</span>
                  <input
                    value={settingsForm.model}
                    maxLength={200}
                    placeholder="deepseek-chat / Qwen/Qwen2.5-7B-Instruct"
                    onChange={(event) =>
                      setSettingsForm({
                        ...settingsForm,
                        model: event.target.value,
                      })
                    }
                  />
                </label>

                <label className="field">
                  <span>Base URL（留空用默认地址）</span>
                  <input
                    value={settingsForm.base_url}
                    maxLength={2048}
                    placeholder="https://api.deepseek.com/v1"
                    onChange={(event) =>
                      setSettingsForm({
                        ...settingsForm,
                        base_url: event.target.value,
                      })
                    }
                  />
                </label>

                <label className="field">
                  <span>API Key</span>
                  <input
                    type="password"
                    value={settingsForm.api_key}
                    maxLength={2048}
                    autoComplete="off"
                    placeholder={
                      settings?.api_key_configured
                        ? `已配置 ${settings.api_key_hint ?? ""}，留空不修改`
                        : "sk-..."
                    }
                    onChange={(event) =>
                      setSettingsForm({
                        ...settingsForm,
                        api_key: event.target.value,
                      })
                    }
                  />
                </label>

                {!canSubmitSettings && (
                  <p className="hint">真实模型必须填写 Model</p>
                )}

                {settingsMessage && (
                  <p className="settings-message">{settingsMessage}</p>
                )}

                <div className="actions">
                  <button
                    type="button"
                    onClick={saveSettings}
                    disabled={!canSubmitSettings || settingsSaving}
                  >
                    {settingsSaving ? "保存中……" : "保存"}
                  </button>
                  <button
                    type="button"
                    className="secondary"
                    onClick={testSettings}
                    disabled={!canSubmitSettings || settingsTesting || settingsSaving}
                  >
                    {settingsTesting ? "测试中……" : "测试连接"}
                  </button>
                  <button
                    type="button"
                    className="secondary"
                    onClick={clearApiKey}
                    disabled={!settings?.api_key_configured || settingsSaving}
                  >
                    清除密钥
                  </button>
                  <button
                    type="button"
                    className="secondary"
                    onClick={resetSettings}
                    disabled={settingsSaving}
                  >
                    恢复 .env
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}