/**
 * Wiki type definitions for the DeepWiki frontend integration.
 * Models wiki structures generated from ingested RAG data.
 */

export interface WikiPage {
  id: string;
  title: string;
  content: string;
  importance: "high" | "medium" | "low";
  relatedPages: string[];
  sourceDocuments: string[];
  parentId?: string;
  isSection?: boolean;
  children?: string[];
}

export interface WikiSection {
  id: string;
  title: string;
  pages: string[];
  subsections?: string[];
}

export interface WikiStructure {
  id: string;
  title: string;
  description: string;
  pages: WikiPage[];
  sections: WikiSection[];
  rootSections: string[];
}

export interface WikiProject {
  id: string;
  title: string;
  description: string;
  createdAt: string;
  updatedAt: string;
  pageCount: number;
  sourceCount: number;
  filters?: Record<string, string>;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface WikiGenerateRequest {
  title?: string;
  filters?: Record<string, string>;
  search_type?: string;
  match_count?: number;
}
