"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import DocumentSidebar from "@/components/DocumentSidebar";
import ChatWindow from "@/components/ChatWindow";
import { getSession, type Session } from "@/lib/api";
import Link from "next/link";

export default function SessionPage() {
  const params = useParams();
  const sessionId = params?.session_id as string;

  const [session, setSession] = useState<Session | null>(null);
  const [sessionError, setSessionError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const fetchSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      const data = await getSession(sessionId);
      setSession(data);
      setSessionError("");
    } catch {
      setSessionError("Session not found.");
    }
  }, [sessionId]);

  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  if (!sessionId) return null;

  return (
    <div className="h-screen flex flex-col overflow-hidden" style={{ backgroundColor: "#fff" }}>

      {/* ── Header ───────────────────────────────────────────────── */}
      <header
        className="flex items-center gap-3 px-4 md:px-6 flex-shrink-0"
        style={{ borderBottom: "1px solid #E5E5E5", height: "52px" }}
      >
        {/* Mobile: hamburger to open sidebar */}
        <button
          className="md:hidden flex items-center justify-center w-8 h-8 rounded-md transition-colors duration-150 flex-shrink-0"
          onClick={() => setSidebarOpen(true)}
          style={{ color: "#666" }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "#000")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "#666")}
          aria-label="Open documents"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>

        {/* Logo */}
        <span
          className="text-xs font-semibold uppercase flex-shrink-0"
          style={{ color: "#666", letterSpacing: "0.1em" }}
        >
          <Link href="/">RESEARCH RAG</Link>
        </span>

        {/* Divider — desktop only */}
        <div className="hidden md:block h-3 flex-shrink-0" style={{ width: "1px", backgroundColor: "#E5E5E5" }} />

        {/* Session info */}
        <div className="flex-1 min-w-0 flex items-center gap-4 justify-center md:justify-start">
          {sessionError ? (
            <span className="text-xs px-2 py-1 rounded-md" style={{ color: "#666", border: "1px solid #E5E5E5" }}>
              {sessionError}
            </span>
          ) : session ? (
            <>
              {/* Session ID — truncated on mobile, full on desktop */}
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="text-xs flex-shrink-0" style={{ color: "#999" }}>Session</span>
                <span
                  className="text-xs font-mono truncate"
                  style={{ color: "#000", letterSpacing: "-0.02em", maxWidth: "120px" }}
                  title={session.id}
                >
                  {session.id}
                </span>
                {/* Full ID — hidden on small screens */}
                <span className="hidden lg:inline text-xs font-mono" style={{ color: "#000", letterSpacing: "-0.02em" }}>
                  {/* (already shown via truncate above, this slot is for wider screens without truncation) */}
                </span>
              </div>

              <div className="hidden sm:block h-3 flex-shrink-0" style={{ width: "1px", backgroundColor: "#E5E5E5" }} />

              <div className="hidden sm:flex items-center gap-1.5 flex-shrink-0">
                <span className="text-xs" style={{ color: "#999" }}>Tokens</span>
                <span className="text-xs font-medium" style={{ color: "#000", letterSpacing: "-0.01em" }}>
                  {session.metrics.total_tokens.toLocaleString()}
                </span>
              </div>

              <div className="hidden sm:block h-3 flex-shrink-0" style={{ width: "1px", backgroundColor: "#E5E5E5" }} />

              <div className="hidden sm:flex items-center gap-1.5 flex-shrink-0">
                <span className="text-xs" style={{ color: "#999" }}>Messages</span>
                <span className="text-xs font-medium" style={{ color: "#000", letterSpacing: "-0.01em" }}>
                  {session.metrics.total_messages}
                </span>
              </div>

              {/* Mobile: compact token + message pill */}
              <div className="sm:hidden flex items-center gap-2">
                <span className="text-xs" style={{ color: "#999" }}>
                  {session.metrics.total_tokens.toLocaleString()} tok · {session.metrics.total_messages} msg
                </span>
              </div>
            </>
          ) : (
            <span className="text-xs" style={{ color: "#999" }}>Loading…</span>
          )}
        </div>
      </header>

      {/* ── Body ─────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        <DocumentSidebar
          sessionId={sessionId}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        <div className="flex flex-col flex-1 overflow-hidden">
          <ChatWindow sessionId={sessionId} onMessageComplete={fetchSession} />
        </div>
      </div>
    </div>
  );
}
