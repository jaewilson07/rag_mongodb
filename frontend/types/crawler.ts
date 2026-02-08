/**
 * Type definitions for the web crawler interface.
 */

export interface CrawlConfig {
  url: string;
  deep: boolean;
  maxDepth: number;
  sourceGroup: string;
  userId?: string;
  orgId?: string;
}

export interface CrawlJob {
  jobId: string;
  status: "queued" | "started" | "finished" | "failed" | "deferred";
  statusUrl: string;
  createdAt?: string;
  updatedAt?: string;
  error?: string;
  result?: CrawlJobResult;
  config?: CrawlConfig;
}

export interface CrawlJobResult {
  documents_ingested?: number;
  chunks_created?: number;
  urls_crawled?: number;
  errors?: string[];
}

export type CrawlHistoryItem = {
  id: string;
  url: string;
  status: string;
  startedAt: string;
  pagesFound?: number;
  sourceGroup?: string;
};
