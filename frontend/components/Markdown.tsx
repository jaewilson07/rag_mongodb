"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { tomorrow } from "react-syntax-highlighter/dist/cjs/styles/prism";
import MermaidDiagram from "./MermaidDiagram";

interface MarkdownProps {
  content: string;
}

const Markdown: React.FC<MarkdownProps> = ({ content }) => {
  const components: React.ComponentProps<typeof ReactMarkdown>["components"] = {
    p({ children, ...props }: { children?: React.ReactNode }) {
      return (
        <p className="mb-3 text-sm leading-relaxed" {...props}>
          {children}
        </p>
      );
    },
    h1({ children, ...props }: { children?: React.ReactNode }) {
      return (
        <h1 className="text-xl font-bold mt-6 mb-3" {...props}>
          {children}
        </h1>
      );
    },
    h2({ children, ...props }: { children?: React.ReactNode }) {
      return (
        <h2 className="text-lg font-bold mt-5 mb-3" {...props}>
          {children}
        </h2>
      );
    },
    h3({ children, ...props }: { children?: React.ReactNode }) {
      return (
        <h3 className="text-base font-semibold mt-4 mb-2" {...props}>
          {children}
        </h3>
      );
    },
    h4({ children, ...props }: { children?: React.ReactNode }) {
      return (
        <h4 className="text-sm font-semibold mt-3 mb-2" {...props}>
          {children}
        </h4>
      );
    },
    ul({ children, ...props }: { children?: React.ReactNode }) {
      return (
        <ul className="list-disc pl-6 mb-4 text-sm space-y-2" {...props}>
          {children}
        </ul>
      );
    },
    ol({ children, ...props }: { children?: React.ReactNode }) {
      return (
        <ol className="list-decimal pl-6 mb-4 text-sm space-y-2" {...props}>
          {children}
        </ol>
      );
    },
    li({ children, ...props }: { children?: React.ReactNode }) {
      return (
        <li className="mb-2 text-sm leading-relaxed" {...props}>
          {children}
        </li>
      );
    },
    a({
      children,
      href,
      ...props
    }: {
      children?: React.ReactNode;
      href?: string;
    }) {
      return (
        <a
          href={href}
          className="text-[var(--accent-primary)] hover:underline font-medium"
          target="_blank"
          rel="noopener noreferrer"
          {...props}
        >
          {children}
        </a>
      );
    },
    blockquote({ children, ...props }: { children?: React.ReactNode }) {
      return (
        <blockquote
          className="border-l-4 border-[var(--border-color)] pl-4 py-1 italic my-4 text-sm opacity-80"
          {...props}
        >
          {children}
        </blockquote>
      );
    },
    table({ children, ...props }: { children?: React.ReactNode }) {
      return (
        <div className="overflow-x-auto my-6 rounded-md">
          <table className="min-w-full text-sm border-collapse" {...props}>
            {children}
          </table>
        </div>
      );
    },
    thead({ children, ...props }: { children?: React.ReactNode }) {
      return (
        <thead className="bg-[var(--background)]/70" {...props}>
          {children}
        </thead>
      );
    },
    th({ children, ...props }: { children?: React.ReactNode }) {
      return (
        <th
          className="px-4 py-3 text-left font-medium border border-[var(--border-color)]"
          {...props}
        >
          {children}
        </th>
      );
    },
    td({ children, ...props }: { children?: React.ReactNode }) {
      return (
        <td className="px-4 py-3 border border-[var(--border-color)]" {...props}>
          {children}
        </td>
      );
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    code(props: any) {
      const { inline, className, children, ...otherProps } = props;
      const match = /language-(\w+)/.exec(className || "");
      const codeContent = children ? String(children).replace(/\n$/, "") : "";

      if (!inline && match && match[1] === "mermaid") {
        return (
          <div className="my-8 bg-[var(--card-bg)] rounded-md overflow-hidden shadow-sm">
            <MermaidDiagram chart={codeContent} />
          </div>
        );
      }

      if (!inline && match) {
        return (
          <div className="my-6 rounded-md overflow-hidden text-sm shadow-sm">
            <div className="bg-gray-800 text-gray-200 px-5 py-2 text-sm flex justify-between items-center">
              <span>{match[1]}</span>
              <button
                onClick={() => navigator.clipboard.writeText(codeContent)}
                className="text-gray-400 hover:text-white"
                title="Copy code"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
            <SyntaxHighlighter
              language={match[1]}
              style={tomorrow}
              customStyle={{ margin: 0, borderRadius: "0 0 0.375rem 0.375rem", padding: "1rem" }}
              showLineNumbers={true}
              wrapLongLines={true}
              {...otherProps}
            >
              {codeContent}
            </SyntaxHighlighter>
          </div>
        );
      }

      return (
        <code
          className="font-mono bg-[var(--background)]/70 px-2 py-0.5 rounded text-pink-500 text-sm border border-[var(--border-color)]"
          {...otherProps}
        >
          {children}
        </code>
      );
    },
  };

  return (
    <div className="wiki-prose max-w-none px-2 py-4">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default Markdown;
