"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";
import MermaidDiagram from "@/components/MermaidDiagram";
import type { WikiProject } from "@/types/wiki";

const DEMO_FLOW_CHART = `graph TD
  A[Ingested Documents] --> B[Knowledge Wiki]
  B --> C[Architecture Diagrams]
  B --> D[Topic Relationships]
  B --> E[Data Flow]
  B --> F[Interactive Q&A]

  style A fill:#f9d3a9,stroke:#d86c1f
  style B fill:#d4a9f9,stroke:#6c1fd8
  style C fill:#a9f9d3,stroke:#1fd86c
  style D fill:#a9d3f9,stroke:#1f6cd8
  style E fill:#f9a9d3,stroke:#d81f6c
  style F fill:#d3f9a9,stroke:#6cd81f`;

const DEMO_SEQUENCE_CHART = `sequenceDiagram
  participant User
  participant Wiki
  participant RAG

  User->>Wiki: Select or Generate Wiki
  Wiki->>RAG: Query ingested documents
  RAG-->>Wiki: Return relevant chunks
  Wiki->>Wiki: Generate structured content
  Wiki-->>User: Display wiki with diagrams

  Note over User,RAG: Knowledge Wiki supports interactive Q&A`;

export default function Home() {
  const router = useRouter();
  const [projects, setProjects] = useState<WikiProject[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [wikiTitle, setWikiTitle] = useState("");
  const [filterSource, setFilterSource] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadProjects = async () => {
      try {
        const res = await fetch("/api/wiki/projects");
        if (res.ok) {
          const data = await res.json();
          setProjects(data.projects || []);
        }
      } catch (err) {
        console.error("Failed to load projects:", err);
      } finally {
        setProjectsLoading(false);
      }
    };
    loadProjects();
  }, []);

  const handleGenerateWiki = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isGenerating) return;
    setIsGenerating(true);
    setError(null);

    try {
      const filters: Record<string, string> = {};
      if (filterSource.trim()) {
        filters.source_type = filterSource.trim();
      }

      const res = await fetch("/api/wiki/structure", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: wikiTitle.trim() || "Knowledge Base Wiki",
          filters,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `Failed to generate wiki structure: ${res.status}`
        );
      }

      const data = await res.json();
      // Store wiki structure in sessionStorage for the wiki page to consume
      sessionStorage.setItem("wikiStructure", JSON.stringify(data));
      router.push(`/wiki/${data.id}`);
    } catch (err) {
      console.error("Error generating wiki:", err);
      setError(
        err instanceof Error ? err.message : "Failed to generate wiki"
      );
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="h-screen paper-texture p-4 md:p-8 flex flex-col">
      {/* Header */}
      <header className="max-w-6xl mx-auto mb-6 h-fit w-full">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-[var(--card-bg)] rounded-lg shadow-custom border border-[var(--border-color)] p-4">
          <div className="flex items-center">
            <div className="bg-[var(--accent-primary)] p-2 rounded-lg mr-3">
              <svg
                className="w-6 h-6 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                />
              </svg>
            </div>
            <div className="mr-6">
              <h1 className="text-xl md:text-2xl font-bold text-[var(--accent-primary)]">
                Knowledge Wiki
              </h1>
              <div className="flex flex-wrap items-baseline gap-x-2 md:gap-x-3 mt-0.5">
                <p className="text-xs text-[var(--muted)] whitespace-nowrap">
                  Generate wikis from your ingested knowledge base
                </p>
                <Link
                  href="/crawler"
                  className="text-xs font-medium text-[var(--accent-primary)] hover:text-[var(--highlight)] hover:underline whitespace-nowrap"
                >
                  Web Crawler
                </Link>
                {projects.length > 0 && (
                  <Link
                    href="/wiki/projects"
                    className="text-xs font-medium text-[var(--accent-primary)] hover:text-[var(--highlight)] hover:underline whitespace-nowrap"
                  >
                    Browse Projects
                  </Link>
                )}
              </div>
            </div>
          </div>

          {/* Generate Wiki Form */}
          <form
            onSubmit={handleGenerateWiki}
            className="flex flex-col gap-3 w-full max-w-3xl"
          >
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="relative flex-1">
                <input
                  type="text"
                  value={wikiTitle}
                  onChange={(e) => setWikiTitle(e.target.value)}
                  placeholder="Wiki title (optional, e.g., 'API Documentation')"
                  className="input-field block w-full pl-10 pr-3 py-2.5 rounded-lg"
                />
                <svg
                  className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--muted)]"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                  />
                </svg>
                {error && (
                  <div className="text-[var(--highlight)] text-xs mt-1">
                    {error}
                  </div>
                )}
              </div>
              <button
                type="submit"
                className="btn-primary px-6 py-2.5 rounded-lg"
                disabled={isGenerating}
              >
                {isGenerating ? "Generating..." : "Generate Wiki"}
              </button>
            </div>

            {/* Optional filter */}
            <div className="flex gap-2">
              <input
                type="text"
                value={filterSource}
                onChange={(e) => setFilterSource(e.target.value)}
                placeholder="Filter by source type (optional)"
                className="input-field block w-full text-xs py-1.5 rounded"
              />
            </div>
          </form>

          <ThemeToggle />
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl mx-auto w-full overflow-y-auto">
        <div className="min-h-full flex flex-col items-center p-8 pt-10 bg-[var(--card-bg)] rounded-lg shadow-custom card">
          {/* Show projects if available */}
          {!projectsLoading && projects.length > 0 ? (
            <div className="w-full">
              <div className="flex flex-col items-center w-full max-w-2xl mb-8 mx-auto">
                <div className="flex flex-col sm:flex-row items-center mb-6 gap-4">
                  <div className="relative">
                    <div className="absolute -inset-1 bg-[var(--accent-primary)]/20 rounded-full blur-md" />
                    <svg
                      className="w-12 h-12 text-[var(--accent-primary)] relative z-10"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                      />
                    </svg>
                  </div>
                  <div className="text-center sm:text-left">
                    <h2 className="text-2xl font-bold text-[var(--foreground)] font-serif mb-1">
                      Your Knowledge Wikis
                    </h2>
                    <p className="text-[var(--accent-primary)] text-sm max-w-md">
                      Browse previously generated wikis or create a new one
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 w-full">
                {projects.map((project) => (
                  <Link
                    key={project.id}
                    href={`/wiki/${project.id}`}
                    className="card p-4 hover:shadow-lg transition-all"
                  >
                    <h3 className="font-semibold text-[var(--foreground)] mb-1 truncate">
                      {project.title}
                    </h3>
                    <p className="text-xs text-[var(--muted)] mb-2 line-clamp-2">
                      {project.description}
                    </p>
                    <div className="flex justify-between text-xs text-[var(--muted)]">
                      <span>{project.pageCount} pages</span>
                      <span>{project.sourceCount} sources</span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          ) : (
            <>
              {/* Welcome content */}
              <div className="flex flex-col items-center w-full max-w-2xl mb-8">
                <div className="flex flex-col sm:flex-row items-center mb-6 gap-4">
                  <div className="relative">
                    <div className="absolute -inset-1 bg-[var(--accent-primary)]/20 rounded-full blur-md" />
                    <svg
                      className="w-12 h-12 text-[var(--accent-primary)] relative z-10"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                      />
                    </svg>
                  </div>
                  <div className="text-center sm:text-left">
                    <h2 className="text-2xl font-bold text-[var(--foreground)] font-serif mb-1">
                      Welcome to Knowledge Wiki
                    </h2>
                    <p className="text-[var(--accent-primary)] text-sm max-w-md">
                      Transform your ingested data into interactive knowledge wikis
                    </p>
                  </div>
                </div>

                <p className="text-[var(--foreground)] text-center mb-8 text-lg leading-relaxed">
                  Knowledge Wiki automatically generates structured, browsable documentation
                  from any data you&apos;ve ingested into your RAG system. Documents, web
                  pages, Google Drive files - all become searchable, interactive wikis.
                </p>
              </div>

              {/* Quick Start */}
              <div className="w-full max-w-2xl mb-10 bg-[var(--accent-primary)]/5 border border-[var(--accent-primary)]/20 rounded-lg p-5">
                <h3 className="text-sm font-semibold text-[var(--accent-primary)] mb-3 flex items-center">
                  <svg
                    className="h-4 w-4 mr-2"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  How It Works
                </h3>
                <div className="grid grid-cols-1 gap-3 text-sm text-[var(--foreground)]">
                  <div className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[var(--accent-primary)] text-white text-xs flex items-center justify-center font-bold">
                      1
                    </span>
                    <p>
                      <strong>Ingest your data</strong> - Documents, websites, Google
                      Drive files via the ingestion API
                    </p>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[var(--accent-primary)] text-white text-xs flex items-center justify-center font-bold">
                      2
                    </span>
                    <p>
                      <strong>Generate a wiki</strong> - Click &quot;Generate Wiki&quot;
                      to auto-structure your knowledge
                    </p>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[var(--accent-primary)] text-white text-xs flex items-center justify-center font-bold">
                      3
                    </span>
                    <p>
                      <strong>Browse and ask</strong> - Navigate wiki pages, view
                      diagrams, and ask questions
                    </p>
                  </div>
                </div>
              </div>

              {/* Visualization demos */}
              <div className="w-full max-w-2xl mb-8 bg-[var(--background)]/70 rounded-lg p-6 border border-[var(--border-color)]">
                <h3 className="text-base font-semibold text-[var(--foreground)] font-serif mb-4">
                  Advanced Visualization
                </h3>
                <p className="text-sm text-[var(--foreground)] mb-5 leading-relaxed">
                  Generated wikis include Mermaid diagrams for architecture views,
                  data flow visualization, and relationship mapping.
                </p>

                <div className="grid grid-cols-1 gap-6">
                  <div className="bg-[var(--card-bg)] p-4 rounded-lg border border-[var(--border-color)] shadow-custom">
                    <h4 className="text-sm font-medium mb-3 font-serif">
                      Knowledge Flow
                    </h4>
                    <MermaidDiagram chart={DEMO_FLOW_CHART} />
                  </div>

                  <div className="bg-[var(--card-bg)] p-4 rounded-lg border border-[var(--border-color)] shadow-custom">
                    <h4 className="text-sm font-medium mb-3 font-serif">
                      Query Sequence
                    </h4>
                    <MermaidDiagram chart={DEMO_SEQUENCE_CHART} />
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto mt-8 flex flex-col gap-4 w-full">
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4 bg-[var(--card-bg)] rounded-lg p-4 border border-[var(--border-color)] shadow-custom">
          <p className="text-[var(--muted)] text-sm font-serif">
            Knowledge Wiki - Powered by MongoDB RAG Agent
          </p>
          <div className="flex items-center gap-4">
            <Link
              href="/crawler"
              className="text-sm text-[var(--muted)] hover:text-[var(--accent-primary)] transition-colors"
            >
              Web Crawler
            </Link>
            <Link
              href="/wiki/projects"
              className="text-sm text-[var(--muted)] hover:text-[var(--accent-primary)] transition-colors"
            >
              All Projects
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
