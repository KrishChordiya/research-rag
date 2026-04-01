"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { getDocuments, type Document } from "@/lib/api";

interface DocumentSidebarProps {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
}

function StatusBadge({ status }: { status: string }) {
  const isSuccess = status === "successful";
  const isPending =
    status === "pending" || status === "processing" || status === "embedding";

  return (
    <span
      className="inline-block text-xs px-2 py-0.5 rounded-md font-medium"
      style={{
        border: "1px solid #E5E5E5",
        backgroundColor: isSuccess ? "#000" : "transparent",
        color: isSuccess ? "#fff" : "#666",
        transition: "all 150ms",
      }}
    >
      {isSuccess ? "Ready" : isPending ? "Processing…" : status}
    </span>
  );
}

function MetricRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span style={{ color: "#666666", fontSize: "13px" }}>{label}</span>
      <span style={{ fontSize: "14px", fontWeight: 500, letterSpacing: "-0.01em" }}>
        {value}
      </span>
    </div>
  );
}

function DocumentCard({ doc }: { doc: Document }) {
  const [expanded, setExpanded] = useState(false);
  const hasMetrics = doc.metrics && Object.keys(doc.metrics).length > 0;

  return (
    <div className="rounded-md overflow-hidden" style={{ border: "1px solid #E5E5E5" }}>
      <div className="px-3 py-3">
        <div className="flex items-start justify-between gap-2 mb-2">
          <span
            className="text-sm font-medium break-all leading-snug"
            style={{ letterSpacing: "-0.01em", lineHeight: 1.4 }}
          >
            {doc.filename}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <StatusBadge status={doc.status} />
          {hasMetrics && (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="text-xs transition-colors duration-150"
              style={{ color: "#666" }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "#000")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "#666")}
            >
              {expanded ? "Hide" : "Metrics"}
            </button>
          )}
        </div>
      </div>

      {expanded && hasMetrics && doc.metrics && (
        <div className="px-3 pb-3 pt-1" style={{ borderTop: "1px solid #E5E5E5" }}>
          {doc.metrics.parsing_time_seconds !== undefined && (
            <MetricRow label="Parsing" value={`${doc.metrics.parsing_time_seconds.toFixed(2)}s`} />
          )}
          {doc.metrics.total_chunks_yielded !== undefined && (
            <MetricRow label="Chunks" value={doc.metrics.total_chunks_yielded} />
          )}
          {doc.metrics.total_images_extracted !== undefined && (
            <MetricRow label="Images" value={doc.metrics.total_images_extracted} />
          )}
          {doc.metrics.embedding_time_seconds !== undefined && (
            <MetricRow label="Embedding" value={`${doc.metrics.embedding_time_seconds.toFixed(2)}s`} />
          )}
          {doc.metrics.total_vectors_stored !== undefined && (
            <MetricRow label="Vectors" value={doc.metrics.total_vectors_stored} />
          )}
          {doc.metrics.embedding_model_used && (
            <MetricRow label="Model" value={doc.metrics.embedding_model_used} />
          )}
        </div>
      )}
    </div>
  );
}

export default function DocumentSidebar({ sessionId, isOpen, onClose }: DocumentSidebarProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [error, setError] = useState("");
  const [callDocument, setCallDocument] = useState(true); // ✅ control flag

  useEffect(() => {
    if (!callDocument) return; // ✅ stop completely

    const fetchDocs = async () => {
      try {
        const data = await getDocuments(sessionId);
        setDocuments(data.documents);
        setError("");
        console.log(data)
        const allDone = data.documents.every(
          (d) => d.status === "completed"
        );

        if (allDone) {
          setCallDocument(false); // ✅ STOP polling
        }
      } catch {
        setError("Failed to load documents.");
      }
    };

    // initial call
    fetchDocs();

    // polling
    const interval = setInterval(fetchDocs, 5000);

    return () => clearInterval(interval);
  }, [sessionId, callDocument]);

  const sidebarContent = (
    <aside className="flex flex-col h-full bg-white" style={{ borderRight: "1px solid #E5E5E5" }}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-4 flex-shrink-0"
        style={{ borderBottom: "1px solid #E5E5E5" }}
      >
        <h2 className="text-xs font-semibold uppercase" style={{ color: "#666", letterSpacing: "0.1em" }}>
          Documents
        </h2>
        {/* Close — mobile only */}
        <button
          onClick={onClose}
          className="md:hidden flex items-center justify-center w-7 h-7 rounded-md transition-colors duration-150"
          style={{ color: "#666" }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "#000")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "#666")}
          aria-label="Close"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {error && (
          <p className="text-xs px-3 py-2 rounded-md" style={{ color: "#666", border: "1px solid #E5E5E5" }}>
            {error}
          </p>
        )}
        {documents.length === 0 && !error && (
          <p className="text-xs" style={{ color: "#666" }}>Loading…</p>
        )}
        {documents.map((doc) => (
          <DocumentCard key={doc.id} doc={doc} />
        ))}
      </div>
    </aside>
  );

  return (
    <>
      {/* Desktop — always visible inline */}
      <div className="hidden md:flex flex-col h-full flex-shrink-0" style={{ width: "300px" }}>
        {sidebarContent}
      </div>

      {/* Mobile — backdrop */}
      <div
        className="md:hidden fixed inset-0 z-40 transition-opacity duration-200"
        style={{
          backgroundColor: "rgba(0,0,0,0.2)",
          opacity: isOpen ? 1 : 0,
          pointerEvents: isOpen ? "auto" : "none",
        }}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Mobile — slide-in drawer */}
      <div
        className="md:hidden fixed inset-y-0 left-0 z-50 flex flex-col"
        style={{
          width: "min(300px, 85vw)",
          transform: isOpen ? "translateX(0)" : "translateX(-100%)",
          transition: "transform 220ms cubic-bezier(0.4,0,0.2,1)",
        }}
      >
        {sidebarContent}
      </div>
    </>
  );
}
