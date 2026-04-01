"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import UploadBox from "@/components/UploadBox";
import { uploadDocuments } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  const handleStart = async () => {
    if (files.length === 0 || isUploading) return;
    setIsUploading(true);
    setError("");

    try {
      const result = await uploadDocuments(files);
      router.push(`/session/${result.session_id}`);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Upload failed. Please try again.";
      setError(msg);
      setIsUploading(false);
    }
  };

  const canStart = files.length > 0 && !isUploading;

  return (
    <div className="h-screen overflow-y-auto flex flex-col" style={{ backgroundColor: "#fff" }}>

      {/* Top bar */}
      <header
        className="flex items-center justify-between px-5 sm:px-8 py-4 flex-shrink-0"
        style={{ borderBottom: "1px solid #E5E5E5" }}
      >
        <span className="text-xs font-semibold uppercase" style={{ color: "#666", letterSpacing: "0.1em" }}>
          RESEARCH RAG
        </span>
        <span className="text-xs hidden sm:block" style={{ color: "#999", letterSpacing: "-0.01em" }}>
          Research Paper Intelligence
        </span>
      </header>

      {/* Main */}
      <main className="flex-1 flex flex-col items-center justify-center px-5 sm:px-8 py-10">
        <div className="w-full max-w-lg">

          {/* Hero */}
          <div className="mb-10 sm:mb-12">
            <h1
              className="font-semibold mb-5"
              style={{
                fontSize: "clamp(2rem, 6vw, 3rem)",
                letterSpacing: "-0.04em",
                lineHeight: 1.05,
                color: "#000",
              }}
            >
              Specialised RAG
              <br />
              for Research
              <br />
              Papers.
            </h1>

            <ul className="space-y-2 mt-5">
              {[
                "Context-aware answers",
                "Multi-document reasoning",
                "Fast retrieval pipeline",
              ].map((feature) => (
                <li key={feature} className="flex items-center gap-2.5">
                  <span className="text-xs" style={{ color: "#000" }}>→</span>
                  <span className="text-sm" style={{ color: "#666", letterSpacing: "-0.01em" }}>
                    {feature}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {/* Upload */}
          <div className="mb-5">
            <UploadBox
              files={files}
              onFilesChange={setFiles}
              error={error}
              onErrorChange={setError}
            />
          </div>

          {/* CTA */}
          <button
            onClick={handleStart}
            disabled={!canStart}
            className="w-full py-3 rounded-md text-sm font-medium transition-all duration-150"
            style={{
              backgroundColor: canStart ? "#000" : "#E5E5E5",
              color: canStart ? "#fff" : "#999",
              cursor: canStart ? "pointer" : "not-allowed",
              letterSpacing: "-0.01em",
            }}
            onMouseEnter={(e) => { if (canStart) e.currentTarget.style.backgroundColor = "#222"; }}
            onMouseLeave={(e) => { if (canStart) e.currentTarget.style.backgroundColor = "#000"; }}
          >
            {isUploading ? "Uploading…" : "Start Session"}
          </button>
        </div>
      </main>
    </div>
  );
}
