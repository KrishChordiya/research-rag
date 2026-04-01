"use client";

import React, { useCallback, useRef, useState } from "react";

interface UploadBoxProps {
  files: File[];
  onFilesChange: (files: File[]) => void;
  error: string;
  onErrorChange: (error: string) => void;
}

const MAX_FILES = 3;

export default function UploadBox({
  files,
  onFilesChange,
  error,
  onErrorChange,
}: UploadBoxProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndAdd = useCallback(
    (incoming: FileList | File[]) => {
      onErrorChange("");
      const arr = Array.from(incoming);

      const nonPdfs = arr.filter(
        (f) => f.type !== "application/pdf" && !f.name.endsWith(".pdf")
      );
      if (nonPdfs.length > 0) {
        onErrorChange("Only PDF files are supported.");
        return;
      }

      const merged = [...files, ...arr];
      const unique = merged.filter(
        (f, i, self) => self.findIndex((x) => x.name === f.name) === i
      );

      if (unique.length > MAX_FILES) {
        onErrorChange("Maximum 3 files allowed.");
        return;
      }

      onFilesChange(unique);
    },
    [files, onFilesChange, onErrorChange]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      validateAndAdd(e.dataTransfer.files);
    },
    [validateAndAdd]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) validateAndAdd(e.target.files);
    e.target.value = "";
  };

  const removeFile = (idx: number) => {
    onErrorChange("");
    onFilesChange(files.filter((_, i) => i !== idx));
  };

  return (
    <div className="w-full">
      {/* Drop zone */}
      <div
        onClick={() => inputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        style={{
          border: `1px solid ${isDragging ? "#000" : "#E5E5E5"}`,
          backgroundColor: isDragging ? "#F8F8F8" : "#FFFFFF",
          transition: "all 150ms ease",
        }}
        className="rounded-md p-10 text-center cursor-pointer select-none"
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          onChange={handleInputChange}
          className="hidden"
        />

        {/* Upload icon */}
        <div className="flex justify-center mb-4">
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ color: "#666666" }}
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>

        <p
          className="text-sm font-medium"
          style={{ color: "#000", letterSpacing: "-0.01em" }}
        >
          Drop PDFs here or{" "}
          <span
            style={{ textDecoration: "underline", textUnderlineOffset: "3px" }}
          >
            browse
          </span>
        </p>
        <p className="text-xs mt-1" style={{ color: "#666666" }}>
          Up to 3 PDF files
        </p>
      </div>

      {/* Error */}
      {error && (
        <div
          className="mt-3 px-3 py-2 rounded-md text-xs"
          style={{
            border: "1px solid #E5E5E5",
            color: "#666666",
            letterSpacing: "0",
          }}
        >
          {error}
        </div>
      )}

      {/* File list */}
      {files.length > 0 && (
        <ul className="mt-4 space-y-2">
          {files.map((file, idx) => (
            <li
              key={`${file.name}-${idx}`}
              className="flex items-center justify-between px-3 py-2 rounded-md"
              style={{ border: "1px solid #E5E5E5" }}
            >
              <div className="flex items-center gap-2 min-w-0">
                {/* PDF icon */}
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="flex-shrink-0"
                  style={{ color: "#666" }}
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                <span
                  className="text-sm truncate"
                  style={{ letterSpacing: "-0.01em" }}
                >
                  {file.name}
                </span>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  removeFile(idx);
                }}
                className="ml-3 flex-shrink-0 text-xs transition-colors duration-150"
                style={{ color: "#666" }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.color = "#000")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.color = "#666")
                }
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
