"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import WikiTreeView from "@/components/WikiTreeView";
import AskPanel from "@/components/AskPanel";
import Markdown from "@/components/Markdown";
import ThemeToggle from "@/components/ThemeToggle";
import type { WikiStructure, WikiPage } from "@/types/wiki";

export default function WikiViewerPage() {
  const params = useParams();
  const wikiId = params.id as string;

  const [wikiStructure, setWikiStructure] = useState<WikiStructure | undefined>();
  const [currentPageId, setCurrentPageId] = useState<string | undefined>();
  const [generatedPages, setGeneratedPages] = useState<Record<string, WikiPage>>({});
  const [pagesInProgress, setPagesInProgress] = useState(new Set<string>());
  const [isLoading, setIsLoading] = useState(true);
  const [loadingMessage, setLoadingMessage] = useState("Initializing wiki...");
  const [error, setError] = useState<string | null>(null);
  const [isAskModalOpen, setIsAskModalOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const activeContentRequests = useRef(new Map<string, boolean>()).current;

  // Load wiki structure from session storage or API
  useEffect(() => {
    const loadStructure = async () => {
      try {
        // Try session storage first
        const cached = sessionStorage.getItem("wikiStructure");
        if (cached) {
          const parsed = JSON.parse(cached);
          if (parsed.id === wikiId) {
            setWikiStructure(parsed);
            if (parsed.pages.length > 0) {
              setCurrentPageId(parsed.pages[0].id);
            }
            setIsLoading(false);
            return;
          }
        }

        // Otherwise generate from API
        setLoadingMessage("Generating wiki structure from knowledge base...");
        const res = await fetch("/api/wiki/structure", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: "Knowledge Base Wiki",
            filters: {},
          }),
        });

        if (!res.ok) {
          throw new Error(`Failed to load wiki: ${res.status}`);
        }

        const data = await res.json();
        setWikiStructure(data);
        sessionStorage.setItem("wikiStructure", JSON.stringify(data));

        if (data.pages.length > 0) {
          setCurrentPageId(data.pages[0].id);
        }
      } catch (err) {
        console.error("Error loading wiki:", err);
        setError(err instanceof Error ? err.message : "Failed to load wiki");
      } finally {
        setIsLoading(false);
      }
    };

    loadStructure();
  }, [wikiId]);

  // Generate page content when a page is selected
  const generatePageContent = useCallback(
    async (page: WikiPage) => {
      if (generatedPages[page.id]?.content && generatedPages[page.id].content !== "Loading...") {
        return;
      }

      if (activeContentRequests.get(page.id)) {
        return;
      }

      activeContentRequests.set(page.id, true);
      setPagesInProgress((prev) => new Set(prev).add(page.id));
      setGeneratedPages((prev) => ({
        ...prev,
        [page.id]: { ...page, content: "Loading..." },
      }));

      try {
        const res = await fetch("/api/wiki/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            page_id: page.id,
            page_title: page.title,
            source_documents: page.sourceDocuments || [],
            wiki_title: wikiStructure?.title || "Knowledge Base",
          }),
        });

        if (!res.ok) {
          throw new Error(`Error generating page: ${res.status}`);
        }

        // Stream the response
        const reader = res.body?.getReader();
        const decoder = new TextDecoder();
        let content = "";

        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            content += decoder.decode(value, { stream: true });
            // Update page content progressively
            setGeneratedPages((prev) => ({
              ...prev,
              [page.id]: { ...page, content },
            }));
          }
        }

        // Clean markdown delimiters
        content = content
          .replace(/^```markdown\s*/i, "")
          .replace(/```\s*$/i, "");

        setGeneratedPages((prev) => ({
          ...prev,
          [page.id]: { ...page, content },
        }));
      } catch (err) {
        console.error(`Error generating content for ${page.title}:`, err);
        const errorMessage = err instanceof Error ? err.message : "Unknown error";
        setGeneratedPages((prev) => ({
          ...prev,
          [page.id]: {
            ...page,
            content: `Error generating content: ${errorMessage}`,
          },
        }));
      } finally {
        activeContentRequests.delete(page.id);
        setPagesInProgress((prev) => {
          const next = new Set(prev);
          next.delete(page.id);
          return next;
        });
      }
    },
    [generatedPages, wikiStructure, activeContentRequests]
  );

  // Auto-generate content when page is selected
  useEffect(() => {
    if (currentPageId && wikiStructure) {
      const page = wikiStructure.pages.find((p) => p.id === currentPageId);
      if (page) {
        generatePageContent(page);
      }
    }
  }, [currentPageId, wikiStructure, generatePageContent]);

  // Close modal on escape
  useEffect(() => {
    const handleEsc = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsAskModalOpen(false);
      }
    };

    if (isAskModalOpen) {
      window.addEventListener("keydown", handleEsc);
    }
    return () => window.removeEventListener("keydown", handleEsc);
  }, [isAskModalOpen]);

  const handlePageSelect = (pageId: string) => {
    setCurrentPageId(pageId);
    // Scroll to top
    const content = document.getElementById("wiki-content");
    if (content) {
      content.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const currentPage = currentPageId
    ? generatedPages[currentPageId] ||
      wikiStructure?.pages.find((p) => p.id === currentPageId)
    : undefined;

  const handleExport = () => {
    if (!wikiStructure) return;

    let markdown = `# ${wikiStructure.title}\n\n${wikiStructure.description}\n\n---\n\n`;

    for (const page of wikiStructure.pages) {
      const generated = generatedPages[page.id];
      if (generated?.content && generated.content !== "Loading...") {
        markdown += `## ${page.title}\n\n${generated.content}\n\n---\n\n`;
      }
    }

    const blob = new Blob([markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${wikiStructure.title.replace(/\s+/g, "-").toLowerCase()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="h-screen paper-texture flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-[var(--accent-primary)] border-t-transparent mx-auto mb-4" />
          <p className="text-[var(--foreground)] text-lg font-serif">
            {loadingMessage}
          </p>
          <p className="text-[var(--muted)] text-sm mt-2">
            Analyzing your knowledge base...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen paper-texture flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-[var(--highlight)] text-5xl mb-4">!</div>
          <h2 className="text-xl font-bold text-[var(--foreground)] mb-2">
            Error Loading Wiki
          </h2>
          <p className="text-[var(--muted)] mb-4">{error}</p>
          <Link href="/" className="btn-primary px-6 py-2 rounded-lg inline-block">
            Back to Home
          </Link>
        </div>
      </div>
    );
  }

  if (!wikiStructure) {
    return (
      <div className="h-screen paper-texture flex items-center justify-center">
        <div className="text-center">
          <p className="text-[var(--muted)]">No wiki data found.</p>
          <Link href="/" className="btn-primary px-6 py-2 rounded-lg inline-block mt-4">
            Back to Home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col paper-texture">
      {/* Top bar */}
      <header className="flex items-center justify-between px-4 py-3 bg-[var(--card-bg)] border-b border-[var(--border-color)] shadow-custom">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="text-[var(--muted)] hover:text-[var(--accent-primary)] transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
          </Link>
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="text-[var(--muted)] hover:text-[var(--accent-primary)] transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div>
            <h1 className="text-lg font-bold text-[var(--accent-primary)] font-serif">
              {wikiStructure.title}
            </h1>
            <p className="text-xs text-[var(--muted)] max-w-md truncate">
              {wikiStructure.description}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsAskModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-[var(--accent-primary)] text-white hover:bg-[var(--accent-primary)]/90 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            Ask
          </button>
          <button
            onClick={handleExport}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm border border-[var(--border-color)] text-[var(--foreground)] hover:bg-[var(--background)] transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Export
          </button>
          <ThemeToggle />
        </div>
      </header>

      {/* Main content area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        {isSidebarOpen && (
          <aside className="w-72 flex-shrink-0 bg-[var(--card-bg)] border-r border-[var(--border-color)] overflow-y-auto p-4">
            <div className="mb-4">
              <h2 className="text-sm font-semibold text-[var(--muted)] uppercase tracking-wider mb-3">
                Pages
              </h2>
            </div>
            <WikiTreeView
              wikiStructure={wikiStructure}
              currentPageId={currentPageId}
              onPageSelect={handlePageSelect}
            />
          </aside>
        )}

        {/* Wiki content */}
        <main
          id="wiki-content"
          className="flex-1 overflow-y-auto p-6 md:p-8 lg:p-12"
        >
          {currentPage ? (
            <div className="max-w-4xl mx-auto">
              {/* Page header */}
              <div className="mb-6 pb-4 border-b border-[var(--border-color)]">
                <div className="flex items-center gap-2 mb-2">
                  <div
                    className={`w-3 h-3 rounded-full ${
                      currentPage.importance === "high"
                        ? "bg-[#9b7cb9]"
                        : currentPage.importance === "medium"
                        ? "bg-[#d7c4bb]"
                        : "bg-[#e8927c]"
                    }`}
                  />
                  <span className="text-xs text-[var(--muted)] uppercase tracking-wider">
                    {currentPage.importance} importance
                  </span>
                </div>
                <h1 className="text-2xl font-bold text-[var(--foreground)] font-serif">
                  {currentPage.title}
                </h1>
              </div>

              {/* Page content */}
              {pagesInProgress.has(currentPage.id) &&
              currentPage.content === "Loading..." ? (
                <div className="flex items-center gap-3 py-8">
                  <div className="animate-spin rounded-full h-6 w-6 border-2 border-[var(--accent-primary)] border-t-transparent" />
                  <span className="text-[var(--muted)]">
                    Generating content for {currentPage.title}...
                  </span>
                </div>
              ) : (
                <Markdown
                  content={currentPage.content || "No content available yet."}
                />
              )}

              {/* Related pages */}
              {currentPage.relatedPages &&
                currentPage.relatedPages.length > 0 && (
                  <div className="mt-8 pt-4 border-t border-[var(--border-color)]">
                    <h3 className="text-sm font-semibold text-[var(--muted)] mb-2">
                      Related Pages
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {currentPage.relatedPages.map((relatedId) => {
                        const relatedPage = wikiStructure.pages.find(
                          (p) => p.id === relatedId
                        );
                        if (!relatedPage) return null;
                        return (
                          <button
                            key={relatedId}
                            onClick={() => handlePageSelect(relatedId)}
                            className="text-xs px-3 py-1.5 rounded-full border border-[var(--border-color)] text-[var(--foreground)] hover:bg-[var(--accent-primary)]/10 hover:border-[var(--accent-primary)]/30 transition-colors"
                          >
                            {relatedPage.title}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-[var(--muted)]">
              <p>Select a page from the sidebar to view its content.</p>
            </div>
          )}
        </main>
      </div>

      {/* Ask Modal */}
      {isAskModalOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center p-4">
          <div className="bg-[var(--card-bg)] rounded-t-xl sm:rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden border border-[var(--border-color)]">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-color)]">
              <h3 className="font-semibold text-[var(--foreground)]">
                Ask about {wikiStructure.title}
              </h3>
              <button
                onClick={() => setIsAskModalOpen(false)}
                className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="overflow-y-auto max-h-[70vh]">
              <AskPanel
                wikiTitle={wikiStructure.title}
                wikiContext={wikiStructure.description}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
