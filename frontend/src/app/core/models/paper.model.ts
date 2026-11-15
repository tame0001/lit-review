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
