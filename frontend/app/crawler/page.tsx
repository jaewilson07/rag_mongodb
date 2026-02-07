"use client";

import React, { useState, useCallback, useRef, useEffect } from "react";
import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";
import CrawlJobCard from "@/components/CrawlJobCard";
import type { CrawlJob, CrawlConfig } from "@/types/crawler";

/* ------------------------------------------------------------------ */
/*  Algolia-inspired Web Crawler UI                                    */
/* ------------------------------------------------------------------ */

export default function CrawlerPage() {
  // ---- URL input state ----
  const [url, setUrl] = useState("");
  const [urlError, setUrlError] = useState<string | null>(null);
  const [urlValid, setUrlValid] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // ---- Configuration state (Algolia-style panel) ----
  const [showConfig, setShowConfig] = useState(false);
  const [deepCrawl, setDeepCrawl] = useState(false);
  const [maxDepth, setMaxDepth] = useState(2);
  const [sourceGroup, setSourceGroup] = useState("");
  const [userId, setUserId] = useState("");
  const [orgId, setOrgId] = useState("");

  // ---- Jobs state ----
  const [jobs, setJobs] = useState<CrawlJob[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // ---- URL validation ----
  useEffect(() => {
    if (!url.trim()) {
      setUrlValid(false);
      setUrlError(null);
      return;
    }
    try {
      const parsed = new URL(
        url.startsWith("http") ? url : `https://${url}`
      );
      if (!parsed.hostname.includes(".")) {
        setUrlError("Enter a valid domain");
        setUrlValid(false);
      } else {
        setUrlError(null);
        setUrlValid(true);
      }
    } catch {
      setUrlError("Enter a valid URL");
      setUrlValid(false);
    }
  }, [url]);

  // ---- Load persisted jobs from sessionStorage ----
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem("crawlJobs");
      if (saved) setJobs(JSON.parse(saved));
    } catch {}
  }, []);

  useEffect(() => {
    try {
      sessionStorage.setItem("crawlJobs", JSON.stringify(jobs));
    } catch {}
  }, [jobs]);

  // ---- Refresh job status ----
  const refreshJob = useCallback(async (jobId: string) => {
    try {
      const res = await fetch(`/api/ingest/jobs/${jobId}`);
      if (!res.ok) return;
      const data = await res.json();
      setJobs((prev) =>
        prev.map((j) =>
          j.jobId === jobId
            ? {
                ...j,
                status: data.status,
                createdAt: data.created_at,
                updatedAt: data.updated_at,
                error: data.error,
                result: data.result,
              }
            : j
        )
      );
    } catch (err) {
      console.error("Failed to refresh job:", err);
    }
  }, []);

  // ---- Submit crawl ----
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlValid || isSubmitting) return;

    setIsSubmitting(true);
    setSubmitError(null);

    const normalizedUrl = url.startsWith("http") ? url : `https://${url}`;

    const config: CrawlConfig = {
      url: normalizedUrl,
      deep: deepCrawl,
      maxDepth,
      sourceGroup: sourceGroup || new URL(normalizedUrl).hostname,
      userId: userId || undefined,
      orgId: orgId || undefined,
    };

    try {
      const res = await fetch("/api/ingest/web", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: normalizedUrl,
          deep: deepCrawl,
          max_depth: deepCrawl ? maxDepth : undefined,
          source_group: config.sourceGroup,
          user_id: config.userId,
          org_id: config.orgId,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `Error ${res.status}` }));
        throw new Error(err.detail || `Failed: ${res.status}`);
      }

      const data = await res.json();

      const newJob: CrawlJob = {
        jobId: data.job_id,
        status: data.status as CrawlJob["status"],
        statusUrl: data.status_url,
        createdAt: new Date().toISOString(),
        config,
      };

      setJobs((prev) => [newJob, ...prev]);
      setUrl("");
      setShowConfig(false);
    } catch (err) {
      console.error("Submit error:", err);
      setSubmitError(err instanceof Error ? err.message : "Failed to start crawl");
    } finally {
      setIsSubmitting(false);
    }
  };

  // ---- Derived state ----
  const activeJobs = jobs.filter((j) => j.status === "started" || j.status === "queued");
  const completedJobs = jobs.filter((j) => j.status === "finished" || j.status === "failed");

  // ---- Render ----
  return (
    <div className="min-h-screen bg-gray-50">
      {/* ===== Top navigation bar ===== */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-6">
              <Link href="/" className="flex items-center gap-2 group">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
                  <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                </div>
                <span className="text-sm font-semibold text-gray-700 group-hover:text-indigo-600 transition-colors">
                  Knowledge Wiki
                </span>
              </Link>

              <div className="hidden sm:flex items-center gap-1 text-sm">
                <Link href="/" className="px-3 py-1.5 rounded-md text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors">
                  Wiki
                </Link>
                <span className="px-3 py-1.5 rounded-md text-indigo-600 bg-indigo-50 font-medium">
                  Crawler
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {activeJobs.length > 0 && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
                  </span>
                  {activeJobs.length} active
                </span>
              )}
              <ThemeToggle />
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* ===== Hero / URL Input section ===== */}
        <div className="mb-10">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Web Crawler</h1>
            <p className="mt-1 text-sm text-gray-500">
              Crawl any website and ingest its content into your knowledge base. Configure depth, filters, and watch progress in real-time.
            </p>
          </div>

          {/* URL Input Card — Algolia style */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            <form onSubmit={handleSubmit}>
              {/* Main URL bar */}
              <div className="p-5">
                <label htmlFor="crawl-url" className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                  Website URL
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg className={`w-5 h-5 transition-colors ${urlValid ? "text-emerald-500" : "text-gray-300"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                    </svg>
                  </div>
                  <input
                    ref={inputRef}
                    id="crawl-url"
                    type="text"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://docs.example.com"
                    className="block w-full pl-12 pr-36 py-3.5 text-base border border-gray-200 rounded-xl bg-gray-50 text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 transition-all"
                    autoFocus
                  />
                  <div className="absolute inset-y-0 right-0 flex items-center pr-2 gap-1.5">
                    <button
                      type="button"
                      onClick={() => setShowConfig(!showConfig)}
                      className={`px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                        showConfig
                          ? "bg-indigo-100 text-indigo-700 border border-indigo-200"
                          : "bg-white text-gray-500 border border-gray-200 hover:bg-gray-50 hover:text-gray-700"
                      }`}
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                    </button>
                    <button
                      type="submit"
                      disabled={!urlValid || isSubmitting}
                      className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
                        urlValid && !isSubmitting
                          ? "bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm shadow-indigo-200"
                          : "bg-gray-100 text-gray-400 cursor-not-allowed"
                      }`}
                    >
                      {isSubmitting ? (
                        <span className="flex items-center gap-2">
                          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </svg>
                          Starting...
                        </span>
                      ) : (
                        "Start Crawl"
                      )}
                    </button>
                  </div>
                </div>
                {urlError && (
                  <p className="mt-1.5 text-xs text-red-500 flex items-center gap-1">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                    {urlError}
                  </p>
                )}
                {submitError && (
                  <p className="mt-1.5 text-xs text-red-500 flex items-center gap-1">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    {submitError}
                  </p>
                )}
              </div>

              {/* ---- Configuration panel (Algolia-style expandable) ---- */}
              {showConfig && (
                <div className="border-t border-gray-100 bg-gray-50/50 px-5 py-5">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    {/* Deep Crawl toggle */}
                    <div>
                      <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                        Crawl Mode
                      </label>
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          onClick={() => setDeepCrawl(false)}
                          className={`flex-1 px-4 py-2.5 rounded-lg text-sm font-medium border transition-all ${
                            !deepCrawl
                              ? "bg-white border-indigo-300 text-indigo-700 shadow-sm"
                              : "bg-white/50 border-gray-200 text-gray-500 hover:border-gray-300"
                          }`}
                        >
                          <div className="flex items-center justify-center gap-2">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            Single Page
                          </div>
                        </button>
                        <button
                          type="button"
                          onClick={() => setDeepCrawl(true)}
                          className={`flex-1 px-4 py-2.5 rounded-lg text-sm font-medium border transition-all ${
                            deepCrawl
                              ? "bg-white border-indigo-300 text-indigo-700 shadow-sm"
                              : "bg-white/50 border-gray-200 text-gray-500 hover:border-gray-300"
                          }`}
                        >
                          <div className="flex items-center justify-center gap-2">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                            </svg>
                            Deep Crawl
                          </div>
                        </button>
                      </div>
                    </div>

                    {/* Max Depth */}
                    <div>
                      <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                        Max Depth
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          type="range"
                          min={1}
                          max={5}
                          value={maxDepth}
                          onChange={(e) => setMaxDepth(Number(e.target.value))}
                          disabled={!deepCrawl}
                          className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600 disabled:opacity-40"
                        />
                        <span className={`text-sm font-mono font-bold min-w-[2ch] text-center ${
                          deepCrawl ? "text-indigo-600" : "text-gray-300"
                        }`}>
                          {maxDepth}
                        </span>
                      </div>
                      <p className="text-[11px] text-gray-400 mt-1">
                        {deepCrawl
                          ? `Will follow links up to ${maxDepth} level${maxDepth > 1 ? "s" : ""} deep`
                          : "Enable deep crawl to configure depth"}
                      </p>
                    </div>

                    {/* Source Group */}
                    <div>
                      <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                        Source Group
                      </label>
                      <input
                        type="text"
                        value={sourceGroup}
                        onChange={(e) => setSourceGroup(e.target.value)}
                        placeholder="Auto-detected from domain"
                        className="w-full px-3.5 py-2.5 text-sm border border-gray-200 rounded-lg bg-white text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 transition-all"
                      />
                    </div>
                  </div>

                  {/* Advanced options */}
                  <details className="mt-4">
                    <summary className="text-xs font-semibold text-gray-400 uppercase tracking-wider cursor-pointer hover:text-gray-600 transition-colors">
                      Advanced Options
                    </summary>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">User ID (optional)</label>
                        <input
                          type="text"
                          value={userId}
                          onChange={(e) => setUserId(e.target.value)}
                          placeholder="For multi-tenant isolation"
                          className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Org ID (optional)</label>
                        <input
                          type="text"
                          value={orgId}
                          onChange={(e) => setOrgId(e.target.value)}
                          placeholder="Organization namespace"
                          className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400"
                        />
                      </div>
                    </div>
                  </details>
                </div>
              )}
            </form>
          </div>
        </div>

        {/* ===== Active Crawls ===== */}
        {activeJobs.length > 0 && (
          <section className="mb-10">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider flex items-center gap-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500" />
                </span>
                Active Crawls
              </h2>
              <span className="text-xs text-gray-400">{activeJobs.length} running</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {activeJobs.map((job) => (
                <CrawlJobCard key={job.jobId} job={job} onRefresh={refreshJob} />
              ))}
            </div>
          </section>
        )}

        {/* ===== Completed Crawls ===== */}
        {completedJobs.length > 0 && (
          <section className="mb-10">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
                Crawl History
              </h2>
              <button
                onClick={() => setJobs((prev) => prev.filter((j) => j.status === "started" || j.status === "queued"))}
                className="text-xs text-gray-400 hover:text-red-500 transition-colors"
              >
                Clear history
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {completedJobs.map((job) => (
                <CrawlJobCard key={job.jobId} job={job} onRefresh={refreshJob} />
              ))}
            </div>
          </section>
        )}

        {/* ===== Empty state ===== */}
        {jobs.length === 0 && (
          <div className="text-center py-16">
            <div className="w-20 h-20 mx-auto mb-5 rounded-2xl bg-gradient-to-br from-indigo-50 to-violet-50 border border-indigo-100 flex items-center justify-center">
              <svg className="w-10 h-10 text-indigo-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-700 mb-2">
              No crawls yet
            </h3>
            <p className="text-sm text-gray-400 max-w-sm mx-auto mb-6">
              Enter a URL above to start crawling. Pages will be ingested into your knowledge base
              and become available for wiki generation and search.
            </p>

            {/* Feature grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl mx-auto mt-8">
              <div className="bg-white rounded-xl border border-gray-200 p-4 text-left">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center mb-3">
                  <svg className="w-4 h-4 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <h4 className="text-sm font-semibold text-gray-700 mb-1">Fast Extraction</h4>
                <p className="text-xs text-gray-400">Headless browser rendering with content extraction optimized for documentation sites.</p>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-4 text-left">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center mb-3">
                  <svg className="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </div>
                <h4 className="text-sm font-semibold text-gray-700 mb-1">Deep Crawl</h4>
                <p className="text-xs text-gray-400">Follow links up to 5 levels deep. Automatically stays within the same domain.</p>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-4 text-left">
                <div className="w-8 h-8 rounded-lg bg-violet-50 flex items-center justify-center mb-3">
                  <svg className="w-4 h-4 text-violet-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                  </svg>
                </div>
                <h4 className="text-sm font-semibold text-gray-700 mb-1">Auto-Ingest</h4>
                <p className="text-xs text-gray-400">Crawled pages are automatically chunked, embedded, and stored in MongoDB Atlas.</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
