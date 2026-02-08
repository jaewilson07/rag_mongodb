"use client";

import React, { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Markdown from "@/components/Markdown";

interface RelatedLink {
  title: string;
  url: string;
  snippet: string;
}

interface YouTubeMeta {
  video_id: string;
  channel: string;
  thumbnail_url: string;
  duration_seconds: number;
  duration_display: string;
  view_count: number;
  upload_date: string;
  chapters: { title: string; start_time: number; end_time: number }[];
  transcript_language: string;
  has_transcript: boolean;
}

interface Reading {
  id: string;
  url: string;
  title: string;
  summary: string;
  key_points: string[];
  related_links: RelatedLink[];
  tags: string[];
  domain?: string;
  saved_at: string;
  word_count: number;
  status: string;
  media_type?: string;
  youtube?: YouTubeMeta;
}

export default function ReadingDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [reading, setReading] = useState<Reading | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch(`/api/readings/${id}`);
        if (!res.ok) {
          throw new Error(res.status === 404 ? "Reading not found" : `Error ${res.status}`);
        }
        const data = await res.json();
        setReading(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-indigo-500 border-t-transparent" />
      </div>
    );
  }

  if (error || !reading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 mb-4">{error || "Not found"}</p>
          <Link href="/readings" className="text-sm text-indigo-600 hover:underline">
            Back to Readings
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-30">
        <div className="max-w-2xl mx-auto px-4 flex items-center justify-between h-12">
          <Link href="/readings" className="flex items-center gap-2 text-sm text-gray-500 hover:text-indigo-600">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Readings
          </Link>
          <a
            href={reading.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-indigo-600 hover:underline flex items-center gap-1"
          >
            Open Original
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
      </nav>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        {/* Header */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
          <h1 className="text-xl font-bold text-gray-900 mb-2">{reading.title}</h1>
          <div className="flex items-center gap-3 text-xs text-gray-400 mb-3">
            <span>{reading.domain || new URL(reading.url).hostname}</span>
            <span>{new Date(reading.saved_at).toLocaleDateString()}</span>
            {reading.word_count > 0 && <span>{reading.word_count} words</span>}
          </div>
          {reading.tags?.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {reading.tags.map((tag: string) => (
                <span key={tag} className="px-2 py-0.5 text-[10px] font-medium bg-indigo-50 text-indigo-600 rounded-full border border-indigo-100">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* YouTube embed */}
        {reading.media_type === "youtube" && reading.youtube?.video_id && (
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="aspect-video bg-black">
              <iframe
                src={`https://www.youtube.com/embed/${reading.youtube.video_id}`}
                className="w-full h-full"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
                title={reading.title}
              />
            </div>
            <div className="px-5 py-3 flex items-center gap-3 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <svg className="w-3.5 h-3.5 text-red-500" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814z"/>
                </svg>
                <span className="font-medium">{reading.youtube.channel}</span>
              </span>
              {reading.youtube.duration_display && <span>{reading.youtube.duration_display}</span>}
              {reading.youtube.view_count > 0 && <span>{reading.youtube.view_count.toLocaleString()} views</span>}
              {reading.youtube.has_transcript && (
                <span className="px-1.5 py-0.5 rounded bg-green-50 text-green-700 border border-green-200 text-[10px] font-medium">
                  Transcript available
                </span>
              )}
            </div>
            {reading.youtube.chapters.length > 0 && (
              <div className="border-t border-gray-100 px-5 py-3">
                <h4 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2">Chapters</h4>
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {reading.youtube.chapters.map((ch, i) => {
                    const m = Math.floor(ch.start_time / 60);
                    const s = Math.floor(ch.start_time % 60);
                    return (
                      <a
                        key={i}
                        href={`https://www.youtube.com/watch?v=${reading.youtube!.video_id}&t=${Math.floor(ch.start_time)}s`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 text-xs hover:text-indigo-600 transition-colors"
                      >
                        <span className="font-mono text-indigo-500 w-10 text-right flex-shrink-0">
                          {m}:{s.toString().padStart(2, "0")}
                        </span>
                        <span className="text-gray-700">{ch.title}</span>
                      </a>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Summary */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 pt-4 pb-1">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">Summary</h3>
          </div>
          <div className="px-5 pb-5">
            <Markdown content={reading.summary} />
          </div>
        </div>

        {/* Key Points */}
        {reading.key_points?.length > 0 && (
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Key Takeaways</h3>
            <ul className="space-y-2.5">
              {reading.key_points.map((point: string, i: number) => (
                <li key={i} className="flex items-start gap-2.5 text-sm text-gray-700">
                  <span className="w-5 h-5 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center flex-shrink-0 text-[10px] font-bold mt-0.5">
                    {i + 1}
                  </span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Related Links */}
        {reading.related_links?.length > 0 && (
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Related Reading</h3>
            <div className="space-y-2.5">
              {reading.related_links.map((link, i: number) => (
                <a
                  key={i}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-3 rounded-xl border border-gray-100 hover:border-indigo-200 hover:bg-indigo-50/30 transition-all"
                >
                  <p className="text-sm font-medium text-gray-800 mb-0.5 line-clamp-1">{link.title}</p>
                  <p className="text-xs text-gray-500 line-clamp-2">{link.snippet}</p>
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
