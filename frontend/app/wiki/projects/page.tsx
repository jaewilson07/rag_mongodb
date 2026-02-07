"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";
import type { WikiProject } from "@/types/wiki";

export default function WikiProjectsPage() {
  const [projects, setProjects] = useState<WikiProject[]>([]);
  const [isLoading, setIsLoading] = useState(true);

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
        setIsLoading(false);
      }
    };
    loadProjects();
  }, []);

  return (
    <div className="min-h-screen paper-texture p-4 md:p-8">
      <header className="max-w-6xl mx-auto mb-6">
        <div className="flex items-center justify-between bg-[var(--card-bg)] rounded-lg shadow-custom border border-[var(--border-color)] p-4">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="text-[var(--muted)] hover:text-[var(--accent-primary)] transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </Link>
            <h1 className="text-xl font-bold text-[var(--accent-primary)]">
              Wiki Projects
            </h1>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="max-w-6xl mx-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-[var(--accent-primary)] border-t-transparent" />
          </div>
        ) : projects.length === 0 ? (
          <div className="text-center py-20 bg-[var(--card-bg)] rounded-lg border border-[var(--border-color)]">
            <svg
              className="w-16 h-16 text-[var(--muted)] mx-auto mb-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
              />
            </svg>
            <h2 className="text-lg font-semibold text-[var(--foreground)] mb-2">
              No wikis yet
            </h2>
            <p className="text-[var(--muted)] mb-4">
              Generate your first wiki from the home page.
            </p>
            <Link
              href="/"
              className="btn-primary px-6 py-2 rounded-lg inline-block"
            >
              Generate Wiki
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((project) => (
              <Link
                key={project.id}
                href={`/wiki/${project.id}`}
                className="card p-5 hover:shadow-lg transition-all group"
              >
                <h3 className="font-semibold text-[var(--foreground)] mb-2 group-hover:text-[var(--accent-primary)] transition-colors">
                  {project.title}
                </h3>
                <p className="text-xs text-[var(--muted)] mb-3 line-clamp-3">
                  {project.description}
                </p>
                <div className="flex justify-between items-center text-xs text-[var(--muted)] pt-3 border-t border-[var(--border-color)]">
                  <span>{project.pageCount} pages</span>
                  <span>{project.sourceCount} sources</span>
                  <span>
                    {new Date(project.updatedAt).toLocaleDateString()}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
