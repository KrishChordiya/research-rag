"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "@/lib/api";

interface MessageBubbleProps {
  message: Message & { streaming?: boolean; streamingError?: string };
}

function MetricsBar({ metrics }: { metrics: NonNullable<Message["metrics"]> }) {
  const total =
    (metrics.generation_time_seconds ?? 0) + (metrics.retrieval_time ?? 0);

  return (
    <div
      className="mt-3 pt-3 flex flex-wrap gap-x-4 gap-y-1"
      style={{ borderTop: "1px solid #E5E5E5" }}
    >
      {metrics.response_model_used && (
        <span style={{ fontSize: "13px", color: "#666" }}>
          <span style={{ color: "#000", fontWeight: 500 }}>{metrics.response_model_used}</span>
        </span>
      )}
      {metrics.generation_time_seconds !== undefined && (
        <span style={{ fontSize: "13px", color: "#666" }}>
          Gen <span style={{ color: "#000", fontWeight: 500 }}>{metrics.generation_time_seconds.toFixed(2)}s</span>
        </span>
      )}
      {metrics.retrieval_time !== undefined && (
        <span style={{ fontSize: "13px", color: "#666" }}>
          Retrieval <span style={{ color: "#000", fontWeight: 500 }}>{metrics.retrieval_time.toFixed(2)}s</span>
        </span>
      )}
      {total > 0 && (
        <span style={{ fontSize: "13px", color: "#666" }}>
          Total <span style={{ color: "#000", fontWeight: 500 }}>{total.toFixed(2)}s</span>
        </span>
      )}
    </div>
  );
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div
          className="px-4 py-3 rounded-md text-sm"
          style={{
            backgroundColor: "#000",
            color: "#fff",
            letterSpacing: "-0.01em",
            lineHeight: 1.6,
            maxWidth: "min(480px, 85%)",
          }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div
        className="px-4 py-3 rounded-md w-full"
        style={{
          border: "1px solid #E5E5E5",
          backgroundColor: "#fff",
          maxWidth: "min(640px, 100%)",
        }}
      >
        {message.streamingError ? (
          <p className="text-sm" style={{ color: "#666", letterSpacing: "-0.01em" }}>
            {message.streamingError}
          </p>
        ) : message.content === "" && message.streaming ? (
          <p className="text-sm" style={{ color: "#666", letterSpacing: "-0.01em" }}>
            Retrieving context…
          </p>
        ) : (
          <div className="prose-rag text-sm" style={{ lineHeight: 1.65 }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {message.streaming && message.content && (
          <span
            className="inline-block ml-0.5 align-baseline"
            style={{
              width: "2px",
              height: "1em",
              backgroundColor: "#000",
              animation: "blink 1s step-end infinite",
            }}
          />
        )}

        {!message.streaming && message.metrics && (
          <MetricsBar metrics={message.metrics} />
        )}
      </div>
    </div>
  );
}
