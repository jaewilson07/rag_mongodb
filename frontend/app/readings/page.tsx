"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";

interface ReadingItem {
  id: string;
  url: string;
  title: string;
  summary: string;
  tags: string[];
  saved_at: string;
  status: string;
  domain?: string;
}

export default function ReadingsPage() {
  const [readings, setReadings] = useState<ReadingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch("/api/readings");
        if (res.ok) {
          const data = await res.json();
          setReadings(data.readings || []);
          setTotal(data.total || 0);
        }
      } catch (err) {
        console.error("Failed to load readings:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const getDomain = (r: ReadingItem) => {
    if (r.domain) return r.domain;
    try { return new URL(r.url).hostname; } catch { return ""; }
  };

  const formatDate = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
    } catch { return iso; }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-30">
        <div className="max-w-3xl mx-auto px-4 flex items-center justify-between h-14">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                </svg>
              </div>
              <span className="text-sm font-semibold text-gray-700 group-hover:text-indigo-600 transition-colors">
                Readings
              </span>
            </Link>
            <div className="hidden sm:flex items-center gap-1 text-sm">
              <Link href="/" className="px-3 py-1.5 rounded-md text-gray-500 hover:text-gray-700 hover:bg-gray-100">Wiki</Link>
              <Link href="/crawler" className="px-3 py-1.5 rounded-md text-gray-500 hover:text-gray-700 hover:bg-gray-100">Crawler</Link>
              <span className="px-3 py-1.5 rounded-md text-indigo-600 bg-indigo-50 font-medium">Readings</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/save" className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-700 transition-colors">
              + Save Link
            </Link>
            <ThemeToggle />
          </div>
        </div>
      </nav>

      <div className="max-w-3xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-gray-900">My Readings</h1>
            <p className="text-sm text-gray-500">{total} saved article{total !== 1 ? "s" : ""}</p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-indigo-500 border-t-transparent" />
          </div>
        ) : readings.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-gray-200">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-indigo-50 to-violet-50 border border-indigo-100 flex items-center justify-center">
              <svg className="w-8 h-8 text-indigo-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-700 mb-2">No readings yet</h3>
            <p className="text-sm text-gray-400 mb-4">Save your first link to get started.</p>
            <Link href="/save" className="inline-block px-5 py-2.5 rounded-xl text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-700">
              Save a Link
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {readings.map((reading) => (
              <Link
                key={reading.id}
                href={`/readings/${reading.id}`}
                className="block bg-white rounded-xl border border-gray-200 p-4 hover:border-indigo-200 hover:shadow-sm transition-all group"
              >
                <div className="flex items-start gap-3">
                  {/* Favicon placeholder */}
                  <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0 mt-0.5 group-hover:bg-indigo-50 transition-colors">
                    <span className="text-xs font-bold text-gray-400 group-hover:text-indigo-500 uppercase">
                      {getDomain(reading).charAt(0)}
                    </span>
                  </div>

                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-gray-800 group-hover:text-indigo-700 line-clamp-1 mb-0.5">
                      {reading.title}
                    </h3>
                    <p className="text-xs text-gray-500 line-clamp-2 mb-2">
                      {reading.summary}
                    </p>
                    <div className="flex items-center gap-3 text-[11px] text-gray-400">
                      <span>{getDomain(reading)}</span>
                      <span>{formatDate(reading.saved_at)}</span>
                      {reading.tags?.length > 0 && (
                        <div className="flex gap-1">
                          {reading.tags.slice(0, 3).map((tag) => (
                            <span key={tag} className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  <svg className="w-4 h-4 text-gray-300 group-hover:text-indigo-400 flex-shrink-0 mt-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
