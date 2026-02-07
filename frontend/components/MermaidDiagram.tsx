"use client";

import React, { useEffect, useRef, useState } from "react";

interface MermaidDiagramProps {
  chart: string;
  className?: string;
}

const MermaidDiagram: React.FC<MermaidDiagramProps> = ({ chart, className }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const renderChart = async () => {
      if (!containerRef.current || !chart) return;

      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "default",
          securityLevel: "loose",
          fontFamily: "sans-serif",
        });

        const id = `mermaid-${Math.random().toString(36).substring(7)}`;
        const { svg } = await mermaid.render(id, chart);
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
        setError(null);
      } catch (err) {
        console.error("Mermaid render error:", err);
        setError("Failed to render diagram");
        if (containerRef.current) {
          containerRef.current.innerHTML = `<pre class="text-xs text-gray-500 p-4">${chart}</pre>`;
        }
      }
    };

    renderChart();
  }, [chart]);

  if (error) {
    return (
      <div className={`p-4 bg-[var(--background)]/50 rounded-md ${className || ""}`}>
        <p className="text-xs text-[var(--muted)] mb-2">Diagram preview unavailable</p>
        <pre className="text-xs overflow-x-auto">{chart}</pre>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`flex justify-center p-4 ${className || ""}`}
    />
  );
};

export default MermaidDiagram;
