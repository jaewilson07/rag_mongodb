"use client";

import React, { useState, useRef, useEffect } from "react";
import Markdown from "./Markdown";
import type { ChatMessage } from "@/types/wiki";

interface AskPanelProps {
  wikiTitle: string;
  wikiContext?: string;
}

const AskPanel: React.FC<AskPanelProps> = ({ wikiTitle, wikiContext }) => {
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationHistory, setConversationHistory] = useState<ChatMessage[]>(
    []
  );
  const inputRef = useRef<HTMLInputElement>(null);
  const responseRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  useEffect(() => {
    if (responseRef.current) {
      responseRef.current.scrollTop = responseRef.current.scrollHeight;
    }
  }, [response]);

  const clearConversation = () => {
    setQuestion("");
    setResponse("");
    setConversationHistory([]);
    inputRef.current?.focus();
  };

  const downloadResponse = () => {
    const blob = new Blob([response], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `response-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isLoading) return;

    setIsLoading(true);
    setResponse("");

    try {
      const newHistory: ChatMessage[] = [
        ...conversationHistory,
        { role: "user", content: question },
      ];
      setConversationHistory(newHistory);

      const res = await fetch("/api/wiki/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: newHistory.map((msg) => ({
            role: msg.role,
            content: msg.content,
          })),
          wiki_context: wikiContext || wikiTitle,
        }),
      });

      if (!res.ok) {
        throw new Error(`API error: ${res.status}`);
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let fullResponse = "";

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          fullResponse += chunk;
          setResponse(fullResponse);
        }
      }

      setConversationHistory([
        ...newHistory,
        { role: "assistant", content: fullResponse },
      ]);
      setQuestion("");
    } catch (error) {
      console.error("Error during chat:", error);
      setResponse(
        (prev) => prev + "\n\nError: Failed to get a response. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <div className="p-4">
        <form onSubmit={handleSubmit} className="mt-2">
          <div className="relative">
            <input
              ref={inputRef}
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="What would you like to know about this knowledge base?"
              className="block w-full rounded-md border border-[var(--border-color)] bg-[var(--input-bg)] text-[var(--foreground)] px-5 py-3.5 pr-24 text-base shadow-sm focus:border-[var(--accent-primary)] focus:ring-2 focus:ring-[var(--accent-primary)]/30 focus:outline-none transition-all"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !question.trim()}
              className={`absolute right-3 top-1/2 transform -translate-y-1/2 px-4 py-2 rounded-md font-medium text-sm ${
                isLoading || !question.trim()
                  ? "bg-[var(--button-disabled-bg)] text-[var(--button-disabled-text)] cursor-not-allowed"
                  : "bg-[var(--accent-primary)] text-white hover:bg-[var(--accent-primary)]/90 shadow-sm"
              } transition-all duration-200 flex items-center gap-1.5`}
            >
              {isLoading ? (
                <div className="w-4 h-4 rounded-full border-2 border-t-transparent border-white animate-spin" />
              ) : (
                <>
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 5l7 7-7 7M5 5l7 7-7 7"
                    />
                  </svg>
                  <span>Ask</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Response area */}
        {response && (
          <div className="border-t border-[var(--border-color)] mt-4">
            <div ref={responseRef} className="p-4 max-h-[500px] overflow-y-auto">
              <Markdown content={response} />
            </div>

            <div className="p-2 flex justify-end items-center border-t border-[var(--border-color)] gap-2">
              <button
                onClick={downloadResponse}
                className="text-xs text-[var(--muted)] hover:text-green-600 px-2 py-1 rounded-md hover:bg-[var(--background)] flex items-center gap-1"
                title="Download response as markdown"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Download
              </button>
              <button
                onClick={clearConversation}
                className="text-xs text-[var(--muted)] hover:text-[var(--accent-primary)] px-2 py-1 rounded-md hover:bg-[var(--background)]"
              >
                Clear conversation
              </button>
            </div>
          </div>
        )}

        {/* Loading indicator */}
        {isLoading && !response && (
          <div className="p-4 border-t border-[var(--border-color)]">
            <div className="flex items-center space-x-2">
              <div className="animate-pulse flex space-x-1">
                <div className="h-2 w-2 bg-[var(--accent-primary)] rounded-full" />
                <div className="h-2 w-2 bg-[var(--accent-primary)] rounded-full" />
                <div className="h-2 w-2 bg-[var(--accent-primary)] rounded-full" />
              </div>
              <span className="text-xs text-[var(--muted)]">Thinking...</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AskPanel;
