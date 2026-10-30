/**
 * 与后端 schema 对齐的类型。
 *
 * 手写而不是自动生成：目前只有 2 个接口类型，手写成本低于引入
 * openapi-typescript + 生成步骤。等接口多了再考虑生成。
 */
export interface KnowledgeEntry {
  id: string;
  workspace_id: string;
  title: string;
  content: string;
  summary: string | null;
  category: string | null;
  created_at: string;
  updated_at: string;
}

export interface Suggestion {
  title: string | null;
  summary: string | null;
  keywords: string[];
  category: string | null;
  /** 哪个 provider 生成的（fake / deepseek / siliconflow） */
  provider: string;
}