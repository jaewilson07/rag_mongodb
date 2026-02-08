/**
 * API client utilities for communicating with the RAG backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";

export async function fetchWikiStructure(
  filters?: Record<string, string>
): Promise<Response> {
  return fetch(`${API_BASE}/api/wiki/structure`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filters: filters || {} }),
  });
}

export async function fetchWikiPageContent(
  pageId: string,
  pageTitle: string,
  sourceDocuments: string[],
  wikiTitle: string
): Promise<Response> {
  return fetch(`${API_BASE}/api/wiki/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      page_id: pageId,
      page_title: pageTitle,
      source_documents: sourceDocuments,
      wiki_title: wikiTitle,
    }),
  });
}

export async function fetchChatStream(
  messages: { role: string; content: string }[],
  wikiContext?: string
): Promise<Response> {
  return fetch(`${API_BASE}/api/wiki/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages,
      wiki_context: wikiContext || "",
    }),
  });
}

export async function fetchWikiProjects(): Promise<Response> {
  return fetch(`${API_BASE}/api/wiki/projects`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
}
