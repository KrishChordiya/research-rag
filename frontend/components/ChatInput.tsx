"use client";

import React, { useRef, useEffect, KeyboardEvent } from "react";

interface ChatInputProps {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  disabled: boolean;
}

export default function ChatInput({ value, onChange, onSend, disabled }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  }, [value]);

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && value.trim()) onSend();
    }
  };

  const canSend = !disabled && value.trim().length > 0;

  return (
    <div
      className="px-4 sm:px-6 py-3 sm:py-4 flex-shrink-0"
      style={{ borderTop: "1px solid #E5E5E5", backgroundColor: "#fff" }}
    >
      <div
        className="flex items-end gap-2 sm:gap-3 rounded-md px-3 sm:px-4 py-2.5 sm:py-3"
        style={{ border: "1px solid #E5E5E5" }}
      >
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKey}
          disabled={disabled}
          placeholder={disabled ? "Processing…" : "Ask about the research…"}
          className="flex-1 resize-none bg-transparent outline-none text-sm"
          style={{
            color: "#000",
            letterSpacing: "-0.01em",
            lineHeight: 1.6,
            caretColor: "#000",
            /* prevent zoom on iOS when font-size < 16px */
            fontSize: "16px",
          }}
        />
        <button
          onClick={onSend}
          disabled={!canSend}
          className="flex-shrink-0 w-8 h-8 rounded-md flex items-center justify-center transition-all duration-150"
          style={{
            backgroundColor: canSend ? "#000" : "#E5E5E5",
            color: canSend ? "#fff" : "#999",
            cursor: canSend ? "pointer" : "not-allowed",
          }}
          onMouseEnter={(e) => { if (canSend) e.currentTarget.style.backgroundColor = "#333"; }}
          onMouseLeave={(e) => { if (canSend) e.currentTarget.style.backgroundColor = "#000"; }}
          aria-label="Send"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
      <p className="mt-1.5 text-xs text-center hidden sm:block" style={{ color: "#bbb" }}>
        Enter to send · Shift+Enter for newline
      </p>
    </div>
  );
}
