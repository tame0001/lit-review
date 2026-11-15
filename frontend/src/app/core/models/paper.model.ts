export interface PaperSummary {
  key: string;
  version: number | null;
  citekey: string;
  title: string;
  authors: string[];
  author_short: string | null;
  year: number | null;
  doi: string | null;
  publication: string | null;
  tags: string[];
  collections: string[];
  has_obsidian_note: boolean;
  status: 'read' | 'unread' | string;
  priority_score: number;
  manual_bonus: number;
  llm_analyzed: boolean;
  llm_analyzed_at: string | null;
  llm_source: 'full-text' | 'abstract' | 'neither' | string;
  scite_total_citations: number;
}

export interface CollectionItem {
  key: string;
  name: string;
  parent_key: string | null;
}

export interface HealthStatus {
  status: string;
  zotero_mode: string;
  zotero_local_available: boolean;
  obsidian_vault_exists: boolean;
  obsidian_vault_path: string;
}

export interface SyncAllResponse {
  previous_version: number | null;
  new_version: number;
  changed_raw_items: number;
  affected_papers: number;
}

export interface BonusUpdateResponse {
  citekey: string;
  manual_bonus: number;
  priority_score: number;
}

export interface StatusUpdateResponse {
  citekey: string;
  status: 'read' | 'unread';
}

export interface PaperDetailResponse {
  citekey: string;
  metadata: Record<string, unknown>;
  content: string;
  path: string;
}

export interface TagUpdateResponse {
  paper_key: string;
  tags_synced: string[];
  obsidian_sync: Record<string, unknown>;
}

export interface SyncPaperResult {
  key: string;
  citekey: string;
  status: string;
  highlights: number;
  path: string | null;
}

export interface AnalyzePaperResult {
  key: string;
  citekey: string;
  status: string;
  priority_score: number;
  llm_source: string;
  path: string | null;
}
