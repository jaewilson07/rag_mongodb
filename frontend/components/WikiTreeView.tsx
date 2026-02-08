"use client";

import React, { useState } from "react";
import { FaChevronRight, FaChevronDown } from "react-icons/fa";
import type { WikiStructure, WikiPage } from "@/types/wiki";

interface WikiTreeViewProps {
  wikiStructure: WikiStructure;
  currentPageId: string | undefined;
  onPageSelect: (pageId: string) => void;
}

const WikiTreeView: React.FC<WikiTreeViewProps> = ({
  wikiStructure,
  currentPageId,
  onPageSelect,
}) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(wikiStructure.rootSections)
  );

  const toggleSection = (sectionId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    setExpandedSections((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId);
      } else {
        newSet.add(sectionId);
      }
      return newSet;
    });
  };

  const getImportanceDot = (page: WikiPage) => {
    const colors = {
      high: "bg-[#9b7cb9]",
      medium: "bg-[#d7c4bb]",
      low: "bg-[#e8927c]",
    };
    return colors[page.importance] || colors.medium;
  };

  const renderPageButton = (pageId: string) => {
    const page = wikiStructure.pages.find((p) => p.id === pageId);
    if (!page) return null;

    return (
      <button
        key={pageId}
        className={`w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors ${
          currentPageId === pageId
            ? "bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] border border-[var(--accent-primary)]/30"
            : "text-[var(--foreground)] hover:bg-[var(--background)] border border-transparent"
        }`}
        onClick={() => onPageSelect(pageId)}
      >
        <div className="flex items-center">
          <div
            className={`w-2 h-2 rounded-full mr-2 flex-shrink-0 ${getImportanceDot(page)}`}
          />
          <span className="truncate">{page.title}</span>
        </div>
      </button>
    );
  };

  const renderSection = (sectionId: string, level = 0) => {
    const section = wikiStructure.sections.find((s) => s.id === sectionId);
    if (!section) return null;

    const isExpanded = expandedSections.has(sectionId);

    return (
      <div key={sectionId} className="mb-2">
        <button
          className={`flex items-center w-full text-left px-2 py-1.5 rounded-md text-sm font-medium text-[var(--foreground)] hover:bg-[var(--background)]/70 transition-colors ${
            level === 0 ? "bg-[var(--background)]/50" : ""
          }`}
          onClick={(e) => toggleSection(sectionId, e)}
        >
          {isExpanded ? (
            <FaChevronDown className="mr-2 text-xs flex-shrink-0" />
          ) : (
            <FaChevronRight className="mr-2 text-xs flex-shrink-0" />
          )}
          <span className="truncate">{section.title}</span>
        </button>

        {isExpanded && (
          <div
            className={`ml-4 mt-1 space-y-1 ${
              level > 0
                ? "pl-2 border-l border-[var(--border-color)]/30"
                : ""
            }`}
          >
            {section.pages.map((pageId) => renderPageButton(pageId))}
            {section.subsections?.map((subsectionId) =>
              renderSection(subsectionId, level + 1)
            )}
          </div>
        )}
      </div>
    );
  };

  // Fallback to flat list view if no sections defined
  if (
    !wikiStructure.sections ||
    wikiStructure.sections.length === 0 ||
    !wikiStructure.rootSections ||
    wikiStructure.rootSections.length === 0
  ) {
    return (
      <ul className="space-y-2">
        {wikiStructure.pages.map((page) => (
          <li key={page.id}>{renderPageButton(page.id)}</li>
        ))}
      </ul>
    );
  }

  return (
    <div className="space-y-1">
      {wikiStructure.rootSections.map((sectionId) => renderSection(sectionId))}
    </div>
  );
};

export default WikiTreeView;
