"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";
import { getHistory, streamChat, type Message } from "@/lib/api";

type LocalMessage = Message & { streaming?: boolean; streamingError?: string };

interface ChatWindowProps {
  sessionId: string;
  onMessageComplete: () => void;
}

export default function ChatWindow({ sessionId, onMessageComplete }: ChatWindowProps) {
  const [messages, setMessages] = useState<LocalMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const nextIdRef = useRef(-1);

  useEffect(() => {
    getHistory(sessionId)
      .then((data) => {
        setMessages(data.messages || []);
      })
      .catch(() => {
        setMessages([]); // safe fallback
      });
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || isStreaming) return;

    setInput("");

    const userMsg: LocalMessage = {
      id: nextIdRef.current--,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };

    const assistantId = nextIdRef.current--;
    const assistantMsg: LocalMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      streaming: true,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);

    try {
      const gen = streamChat(sessionId, text);

      for await (const event of gen) {
        if (event.type === "token") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: m.content + event.token } : m
            )
          );
        } else if (event.type === "error") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, streaming: false, streamingError: event.detail || "Something went wrong. Please retry." }
                : m
            )
          );
          setIsStreaming(false);
          return;
        } else if (event.type === "end") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, streaming: false, metrics: event.metrics } : m
            )
          );
          onMessageComplete();
        }
      }
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, streaming: false, streamingError: "Response interrupted. Please retry." }
            : m
        )
      );
    } finally {
      setIsStreaming(false);
    }
  }, [input, isStreaming, sessionId, onMessageComplete]);

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 sm:py-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <p
              className="text-sm text-center max-w-xs"
              style={{ color: "#666", letterSpacing: "-0.01em" }}
            >
              Your documents are being processed.
              <br />
              Ask a question once they&apos;re ready.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <ChatInput
        value={input}
        onChange={setInput}
        onSend={sendMessage}
        disabled={isStreaming}
      />
    </div>
  );
}
