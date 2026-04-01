const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface UploadedDocument {
  filename: string;
  document_id: number;
}

export interface UploadResponse {
  status: string;
  session_id: string;
  documents: UploadedDocument[];
}

export interface DocumentMetrics {
  parsing_time_seconds?: number;
  total_chunks_yielded?: number;
  total_images_extracted?: number;
  embedding_time_seconds?: number;
  total_vectors_stored?: number;
  embedding_model_used?: string;
}

export interface Document {
  id: number;
  filename: string;
  status: string;
  metrics?: DocumentMetrics;
}

export interface DocumentsResponse {
  documents: Document[];
}

export interface SessionMetrics {
  total_tokens: number;
  total_messages: number;
}

export interface Session {
  id: string;
  created_at: string;
  metrics: SessionMetrics;
}

export interface MessageMetrics {
  generation_time_seconds?: number;
  response_model_used?: string;
  retrieval_time?: number;
}

export interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  metrics?: MessageMetrics;
  created_at: string;
}

// ─── API Functions ─────────────────────────────────────────────────────────────

export async function uploadDocuments(files: File[]): Promise<UploadResponse> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await fetch(`${BASE_URL}/api/v1/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error?.detail || "Upload failed");
  }

  return response.json();
}

export async function getDocuments(
  sessionId: string
): Promise<DocumentsResponse> {
  const response = await fetch(
    `${BASE_URL}/api/v1/sessions/${sessionId}/documents`
  );
  if (!response.ok) throw new Error("Failed to fetch documents");
  return response.json();
}

export async function getSession(sessionId: string): Promise<Session> {
  const response = await fetch(`${BASE_URL}/api/v1/sessions/${sessionId}`);
  if (!response.ok) throw new Error("Session not found");
  return response.json();
}

export async function getHistory(sessionId: string): Promise<Message[]> {
  const response = await fetch(
    `${BASE_URL}/api/v1/sessions/${sessionId}/history/`
  );
  if (!response.ok) throw new Error("Failed to fetch history");
  return response.json();
}

// ─── SSE Chat ─────────────────────────────────────────────────────────────────

export type SSEEvent =
  | { type: "context"; sources: unknown[] }
  | { type: "token"; token: string }
  | { type: "error"; detail: string }
  | { type: "end"; metrics: MessageMetrics };

export async function* streamChat(
  sessionId: string,
  message: string
): AsyncGenerator<SSEEvent> {
  const response = await fetch(`${BASE_URL}/api/v1/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error?.detail || "Chat request failed");
  }

  if (!response.body) throw new Error("No response body");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    let eventType = "";
    let dataLine = "";

    for (const line of lines) {
      if (line.startsWith("event:")) {
        eventType = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLine = line.slice(5).trim();
      } else if (line === "" && eventType && dataLine) {
        try {
          const parsed = JSON.parse(dataLine);
          if (eventType === "context") {
            yield { type: "context", sources: parsed.sources ?? [] };
          } else if (eventType === "token") {
            yield { type: "token", token: parsed.token ?? "" };
          } else if (eventType === "error") {
            yield { type: "error", detail: parsed.detail ?? "Unknown error" };
          } else if (eventType === "end") {
            yield { type: "end", metrics: parsed.metrics ?? {} };
          }
        } catch {
          // Malformed JSON — skip
        }
        eventType = "";
        dataLine = "";
      }
    }
  }
}
