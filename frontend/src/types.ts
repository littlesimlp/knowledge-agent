/**
 * 与后端 schema 对齐的类型。
 *
 * 手写而不是自动生成：目前只有 4 个类型，手写成本低于引入
 * openapi-typescript + 生成步骤。等接口多了再考虑生成。
 */
export interface KnowledgeEntry {
  id: string;
  workspace_id: string;
  title: string;
  content: string;
  summary: string | null;
  category: string | null;
  keywords: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeSource {
  id: string;
  workspace_id: string;
  source_type: string;
  source_name: string;
  source_url: string | null;
  file_path: string | null;
  source_excerpt: string | null;
  created_at: string;
}

/** 来源详情：比列表多一份完整原文，只在"查看原文"时请求 */
export interface KnowledgeSourceDetail extends KnowledgeSource {
  extracted_text: string | null;
}

/** 上传/导入接口的返回：条目 + 来源 */
export interface ImportResult {
  entry: KnowledgeEntry;
  source: KnowledgeSource;
}

export interface Suggestion {
  title: string | null;
  summary: string | null;
  keywords: string[];
  category: string | null;
  /** 哪个 provider 生成的（fake / deepseek / siliconflow） */
  provider: string;
}

/** PATCH 允许的字段：只提交用户确认过的那些 */
export type EntryPatch = Partial<
  Pick<KnowledgeEntry, "title" | "summary" | "category" | "keywords">
>;