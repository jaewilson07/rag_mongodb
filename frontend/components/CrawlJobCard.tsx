"use client";

import React, { useEffect, useState } from "react";
import type { CrawlJob } from "@/types/crawler";

interface CrawlJobCardProps {
  job: CrawlJob;
  onRefresh: (jobId: string) => void;
}

const statusConfig: Record<string, { color: string; bg: string; label: string; icon: string }> = {
  queued: { color: "text-amber-700", bg: "bg-amber-50 border-amber-200", label: "Queued", icon: "clock" },
  started: { color: "text-blue-700", bg: "bg-blue-50 border-blue-200", label: "Crawling", icon: "spinner" },
  finished: { color: "text-emerald-700", bg: "bg-emerald-50 border-emerald-200", label: "Complete", icon: "check" },
  failed: { color: "text-red-700", bg: "bg-red-50 border-red-200", label: "Failed", icon: "x" },
  deferred: { color: "text-gray-600", bg: "bg-gray-50 border-gray-200", label: "Deferred", icon: "pause" },
};

const CrawlJobCard: React.FC<CrawlJobCardProps> = ({ job, onRefresh }) => {
  const [polling, setPolling] = useState(
    job.status === "queued" || job.status === "started"
  );

  useEffect(() => {
    if (!polling) return;
    const interval = setInterval(() => {
      onRefresh(job.jobId);
    }, 3000);
    return () => clearInterval(interval);
  }, [polling, job.jobId, onRefresh]);

  useEffect(() => {
    if (job.status === "finished" || job.status === "failed") {
      setPolling(false);
    }
  }, [job.status]);

  const cfg = statusConfig[job.status] || statusConfig.queued;

  return (
    <div className={`border rounded-xl p-5 transition-all ${cfg.bg}`}>
      {/* Header row */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2.5">
          {/* Status indicator */}
          {job.status === "started" ? (
            <div className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500" />
            </div>
          ) : (
            <span className={`inline-flex h-3 w-3 rounded-full ${
              job.status === "finished" ? "bg-emerald-500" :
              job.status === "failed" ? "bg-red-500" :
              "bg-amber-400"
            }`} />
          )}
          <span className={`text-xs font-semibold uppercase tracking-wider ${cfg.color}`}>
            {cfg.label}
          </span>
        </div>
        <span className="text-[10px] font-mono text-gray-400">
          {job.jobId.slice(0, 12)}
        </span>
      </div>

      {/* URL */}
      <div className="mb-3">
        <p className="text-sm font-medium text-gray-900 truncate" title={job.config?.url}>
          {job.config?.url || "Unknown URL"}
        </p>
        {job.config?.sourceGroup && (
          <p className="text-xs text-gray-500 mt-0.5">
            Group: {job.config.sourceGroup}
          </p>
        )}
      </div>

      {/* Progress / Result */}
      {job.status === "started" && (
        <div className="mb-3">
          <div className="h-1.5 bg-blue-100 rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 rounded-full animate-pulse" style={{ width: "60%" }} />
          </div>
          <p className="text-xs text-blue-600 mt-1.5">Crawling pages...</p>
        </div>
      )}

      {job.status === "finished" && job.result && (
        <div className="grid grid-cols-3 gap-3 mb-3">
          <div className="text-center p-2 bg-white/60 rounded-lg">
            <p className="text-lg font-bold text-emerald-700">{job.result.urls_crawled ?? "—"}</p>
            <p className="text-[10px] text-gray-500 uppercase tracking-wide">Pages</p>
          </div>
          <div className="text-center p-2 bg-white/60 rounded-lg">
            <p className="text-lg font-bold text-emerald-700">{job.result.documents_ingested ?? "—"}</p>
            <p className="text-[10px] text-gray-500 uppercase tracking-wide">Docs</p>
          </div>
          <div className="text-center p-2 bg-white/60 rounded-lg">
            <p className="text-lg font-bold text-emerald-700">{job.result.chunks_created ?? "—"}</p>
            <p className="text-[10px] text-gray-500 uppercase tracking-wide">Chunks</p>
          </div>
        </div>
      )}

      {job.status === "failed" && job.error && (
        <div className="p-2.5 bg-red-100/60 rounded-lg mb-3">
          <p className="text-xs text-red-700 font-mono">{job.error}</p>
        </div>
      )}

      {/* Config summary */}
      <div className="flex items-center gap-3 text-[11px] text-gray-400">
        {job.config?.deep && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/50 border border-gray-200">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            Depth: {job.config.maxDepth}
          </span>
        )}
        {job.createdAt && (
          <span>{new Date(job.createdAt).toLocaleTimeString()}</span>
        )}
      </div>
    </div>
  );
};

export default CrawlJobCard;
