"use client";

import React, { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import Markdown from "@/components/Markdown";

/**
 * /save — Android Share Target receiver + manual save page.
 *
 * When a user shares a link from any Android app the PWA intercepts
 * it via the Web Share Target API and opens this page with the URL
 * in query params.  The page immediately starts the save-and-research
 * pipeline (crawl → summarise → find related links → ingest).
 */

function SavePageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  // Receive URL from share intent or manual entry
  const sharedUrl = searchParams.get("url") || searchParams.get("text") || "";
  const sharedTitle = searchParams.get("title") || "";

  const [url, setUrl] = useState(sharedUrl);
  const [tags, setTags] = useState("");
  const [saving, setSaving] = useState(false);
  interface SaveResult {
    id: string;
    url: string;
    title: string;
    summary: string;
    key_points: string[];
    related_links: { title: string; url: string; snippet: string }[];
    tags: string[];
    status: string;
  }

  const [result, setResult] = useState<SaveResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [autoStarted, setAutoStarted] = useState(false);

  // Auto-save if URL came from share intent
  useEffect(() => {
    if (sharedUrl && !autoStarted) {
      setAutoStarted(true);
      handleSave(sharedUrl);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sharedUrl]);

  const handleSave = async (saveUrl?: string) => {
    const targetUrl = saveUrl || url;
    if (!targetUrl.trim() || saving) return;

    setSaving(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch("/api/readings/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: targetUrl.startsWith("http") ? targetUrl : `https://${targetUrl}`,
          tags: tags
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean),
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Error ${res.status}`);
      }

      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSave();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Compact mobile-friendly nav */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-30">
        <div className="max-w-2xl mx-auto px-4 flex items-center justify-between h-12">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
              <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
            </div>
            <span className="text-sm font-semibold text-gray-700">Save</span>
          </Link>
          <Link
            href="/readings"
            className="text-xs font-medium text-indigo-600 hover:text-indigo-700"
          >
            My Readings
          </Link>
        </div>
      </nav>

      <div className="max-w-2xl mx-auto px-4 py-6">
        {/* Save form */}
        {!result && (
          <form onSubmit={handleSubmit} className="mb-6">
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="p-4">
                <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1.5">
                  Save & Research
                </label>
                <div className="relative">
                  <input
                    ref={inputRef}
                    type="text"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="Paste a URL to save..."
                    className="block w-full pl-4 pr-24 py-3 text-base border border-gray-200 rounded-xl bg-gray-50 text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400"
                    autoFocus={!sharedUrl}
                  />
                  <button
                    type="submit"
                    disabled={!url.trim() || saving}
                    className={`absolute right-2 top-1/2 -translate-y-1/2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                      url.trim() && !saving
                        ? "bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm"
                        : "bg-gray-100 text-gray-400 cursor-not-allowed"
                    }`}
                  >
                    {saving ? (
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                    ) : (
                      "Save"
                    )}
                  </button>
                </div>
                {/* Tags input */}
                <input
                  type="text"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="Tags (comma-separated, optional)"
                  className="mt-2 block w-full px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400"
                />
              </div>
            </div>

            {error && (
              <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-xl">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}
          </form>
        )}

        {/* Processing indicator */}
        {saving && (
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 mb-6">
            <div className="flex flex-col items-center">
              <div className="relative w-16 h-16 mb-4">
                <div className="absolute inset-0 rounded-full border-4 border-indigo-100" />
                <div className="absolute inset-0 rounded-full border-4 border-t-indigo-500 animate-spin" />
              </div>
              <h3 className="text-base font-semibold text-gray-800 mb-1">
                Saving & Researching
              </h3>
              <p className="text-sm text-gray-500 text-center">
                Crawling page, generating summary, finding related content...
              </p>

              {/* Pipeline steps */}
              <div className="mt-4 w-full max-w-xs space-y-2">
                {["Crawling page content", "Generating AI summary", "Finding related links", "Storing in knowledge base"].map(
                  (step, i) => (
                    <div key={step} className="flex items-center gap-2 text-xs text-gray-500">
                      <div
                        className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${
                          i === 0
                            ? "bg-indigo-100 text-indigo-600"
                            : "bg-gray-100 text-gray-400"
                        }`}
                      >
                        {i === 0 ? (
                          <svg className="w-3 h-3 animate-spin" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </svg>
                        ) : (
                          <span className="text-[10px] font-bold">{i + 1}</span>
                        )}
                      </div>
                      <span>{step}</span>
                    </div>
                  )
                )}
              </div>
            </div>
          </div>
        )}

        {/* Result display */}
        {result && (
          <div className="space-y-4">
            {/* Success header */}
            <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                <svg className="w-4 h-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-emerald-800">Saved & Researched</h3>
                <a
                  href={result.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-emerald-600 hover:underline truncate block"
                >
                  {result.url}
                </a>
              </div>
            </div>

            {/* Title and summary */}
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="p-5">
                <h2 className="text-lg font-bold text-gray-900 mb-3">
                  {result.title}
                </h2>

                {/* Tags */}
                {result.tags && result.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {result.tags.map((tag: string) => (
                      <span
                        key={tag}
                        className="px-2 py-0.5 text-[10px] font-medium bg-indigo-50 text-indigo-600 rounded-full border border-indigo-100"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}

                {/* Summary */}
                <div className="prose prose-sm max-w-none">
                  <Markdown content={result.summary} />
                </div>
              </div>

              {/* Key points */}
              {result.key_points && result.key_points.length > 0 && (
                <div className="border-t border-gray-100 p-5">
                  <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">
                    Key Takeaways
                  </h4>
                  <ul className="space-y-2">
                    {result.key_points.map((point: string, i: number) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                        <span className="w-5 h-5 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center flex-shrink-0 text-[10px] font-bold mt-0.5">
                          {i + 1}
                        </span>
                        <span>{point}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Related links */}
            {result.related_links && result.related_links.length > 0 && (
              <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
                <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">
                  Related Reading
                </h4>
                <div className="space-y-3">
                  {result.related_links.map((link, i: number) => (
                    <a
                      key={i}
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block p-3 rounded-xl border border-gray-100 hover:border-indigo-200 hover:bg-indigo-50/30 transition-all group"
                    >
                      <p className="text-sm font-medium text-gray-800 group-hover:text-indigo-700 mb-0.5 line-clamp-1">
                        {link.title}
                      </p>
                      <p className="text-xs text-gray-500 line-clamp-2">{link.snippet}</p>
                      <p className="text-[10px] text-gray-400 mt-1 truncate">{link.url}</p>
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setResult(null);
                  setUrl("");
                  inputRef.current?.focus();
                }}
                className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium bg-white border border-gray-200 text-gray-700 hover:bg-gray-50 transition-all"
              >
                Save Another
              </button>
              <Link
                href="/readings"
                className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium bg-indigo-600 text-white text-center hover:bg-indigo-700 transition-all"
              >
                View All Readings
              </Link>
            </div>
          </div>
        )}

        {/* Empty state hint */}
        {!saving && !result && !sharedUrl && (
          <div className="text-center py-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-indigo-50 to-violet-50 border border-indigo-100 flex items-center justify-center">
              <svg className="w-8 h-8 text-indigo-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
            </div>
            <h3 className="text-base font-semibold text-gray-700 mb-1">
              Save any link
            </h3>
            <p className="text-sm text-gray-400 max-w-xs mx-auto mb-4">
              Paste a URL above, or use &quot;Share to&quot; from any Android app
              to save and research any page.
            </p>
            <div className="bg-white rounded-xl border border-gray-200 p-4 max-w-xs mx-auto text-left">
              <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                Android Setup
              </h4>
              <ol className="text-xs text-gray-500 space-y-1.5">
                <li>1. Open this page in Chrome on Android</li>
                <li>2. Tap the menu (three dots) and &quot;Add to Home Screen&quot;</li>
                <li>3. Now use &quot;Share&quot; from any app and select Knowledge Wiki</li>
              </ol>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function SavePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-indigo-500 border-t-transparent" />
      </div>
    }>
      <SavePageInner />
    </Suspense>
  );
}
