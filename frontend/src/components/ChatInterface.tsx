"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type MessageRole = "user" | "assistant";
type HealthState = "checking" | "online" | "offline";

interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
}

interface StreamEvent {
  type?: string;
  text?: string;
  message?: string;
  data?: unknown;
  result?: unknown;
}

const MODEL_OPTIONS = [
  { value: "auto", label: "Auto · OmniRoute" },
  { value: "auto/fast", label: "Auto · fast" },
  { value: "auto/cheap", label: "Auto · economical" },
];

function createId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function createSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

function stringifyToolValue(value: unknown): string {
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return "Tool result received";
  }
}

async function consumeSse(
  response: Response,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  if (!response.ok || !response.body) {
    const message = await response.text();
    throw new Error(message || `Backend returned HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const chunk = await reader.read();
    buffer += decoder.decode(chunk.value ?? new Uint8Array(), { stream: !chunk.done });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const dataLine = frame
        .split("\n")
        .find((line) => line.startsWith("data: "));
      if (!dataLine) continue;
      const payload = dataLine.slice(6);
      if (payload === "[DONE]") return;
      try {
        onEvent(JSON.parse(payload) as StreamEvent);
      } catch {
        // Ignore malformed provider frames; the backend emits structured frames.
      }
    }

    if (chunk.done) break;
  }
}

export default function ChatInterface() {
  const [sessionId, setSessionId] = useState<string>(createSessionId);
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const saved = window.localStorage.getItem(`nexus.messages.${sessionId}`);
      return saved ? (JSON.parse(saved) as ChatMessage[]) : [];
    } catch {
      return [];
    }
  });
  const [input, setInput] = useState("");
  const [model, setModel] = useState(MODEL_OPTIONS[0].value);
  const [grillMode, setGrillMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState<HealthState>("checking");
  const [routingMessage, setRoutingMessage] = useState("");
  const [toolLog, setToolLog] = useState<string[]>([]);

  const storageKey = useMemo(() => `nexus.messages.${sessionId}`, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    window.localStorage.setItem(storageKey, JSON.stringify(messages));
  }, [messages, sessionId, storageKey]);

  const checkHealth = useCallback(async () => {
    try {
      const response = await fetch("/api/health", { cache: "no-store" });
      setHealth(response.ok ? "online" : "offline");
    } catch {
      setHealth("offline");
    }
  }, []);

  useEffect(() => {
    const initialCheck = window.setTimeout(() => void checkHealth(), 0);
    const timer = window.setInterval(() => void checkHealth(), 30_000);
    return () => {
      window.clearTimeout(initialCheck);
      window.clearInterval(timer);
    };
  }, [checkHealth]);

  const startNewChat = () => {
    if (loading) return;
    setSessionId(createSessionId());
    setMessages([]);
    setRoutingMessage("");
    setToolLog([]);
  };

  const sendMessage = async () => {
    const message = input.trim();
    if (!message || loading) return;

    const userMessage: ChatMessage = {
      id: createId("user"),
      role: "user",
      content: message,
    };
    const assistantId = createId("assistant");
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
    };
    const history = messages.map(({ role, content }) => ({ role, content }));

    setMessages((current) => [...current, userMessage, assistantMessage]);
    setInput("");
    setLoading(true);
    setRoutingMessage("");
    setToolLog([]);

    try {
      const response = await fetch("/api/chat/tools", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          history,
          session_id: sessionId,
          model,
          grill_mode: grillMode,
        }),
      });

      await consumeSse(response, (event) => {
        if (event.type === "info" && event.message) {
          setRoutingMessage(event.message);
        } else if (event.type === "text" && event.text) {
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantId
                ? { ...item, content: `${item.content}${event.text ?? ""}` }
                : item,
            ),
          );
        } else if (event.type === "tool_call") {
          setToolLog((current) => [
            ...current,
            `Tool dipanggil: ${stringifyToolValue(event.data)}`,
          ]);
        } else if (event.type === "tool_result") {
          setToolLog((current) => [
            ...current,
            `Tool selesai: ${stringifyToolValue(event.result)}`,
          ]);
        } else if (event.type === "error") {
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantId
                ? { ...item, content: event.message ?? "Terjadi kesalahan." }
                : item,
            ),
          );
        }
      });
      void checkHealth();
    } catch (error) {
      const messageText = error instanceof Error ? error.message : "Koneksi gagal.";
      setMessages((current) =>
        current.map((item) =>
          item.id === assistantId ? { ...item, content: messageText } : item,
        ),
      );
      setHealth("offline");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">N</div>
          <div>
            <h1>Nexus AI</h1>
            <p>Rohadi strategic assistant</p>
          </div>
        </div>

        <button className="new-chat" type="button" onClick={startNewChat} disabled={loading}>
          + Percakapan baru
        </button>

        <div className="side-label">Session</div>
        <div className="status-card">
          <div className="status-row">
            <span className={`status-dot ${health}`} />
            <span>{health === "online" ? "Backend online" : health === "checking" ? "Memeriksa backend" : "Backend offline"}</span>
          </div>
          <p className="status-note">
            Riwayat percakapan ini tersimpan di browser. Memory backend mengikuti session ID yang aman dan terbatas.
          </p>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h2>Ruang berpikir Rohadi</h2>
            <p>{routingMessage || "Tanyakan sesuatu, minta riset, atau stress-test rencana Anda."}</p>
          </div>
          <div className="controls">
            <select className="select" value={model} onChange={(event) => setModel(event.target.value)} aria-label="Pilih model">
              {MODEL_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
            <button className="select" type="button" onClick={() => setGrillMode((current) => !current)} aria-pressed={grillMode}>
              {grillMode ? "Grill-Me aktif" : "Grill-Me"}
            </button>
          </div>
        </header>

        <section className="chat" aria-live="polite">
          {messages.length === 0 ? (
            <div className="empty">
              <div>
                <h3>Mulai percakapan yang lebih tajam.</h3>
                <p>Rohadi akan memilih mode reasoning, memakai tools saat diperlukan, dan menjaga jawaban tetap grounded pada konteks Anda.</p>
              </div>
            </div>
          ) : (
            <div className="message-list">
              {messages.map((item) => (
                <article className={`message ${item.role}`} key={item.id}>
                  <div className="avatar">{item.role === "user" ? "Anda" : "R"}</div>
                  <div className={`bubble ${item.content.startsWith("Internal") ? "error" : ""}`}>
                    {item.content || (loading && item.role === "assistant" ? "Rohadi sedang berpikir…" : "")}
                  </div>
                </article>
              ))}
              {toolLog.length > 0 && (
                <div className="tool-log">
                  {toolLog.slice(-4).map((entry, index) => <div key={`${entry}-${index}`}>{entry}</div>)}
                </div>
              )}
            </div>
          )}
        </section>

        <form className="composer" onSubmit={(event) => { event.preventDefault(); void sendMessage(); }}>
          <div className="composer-box">
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void sendMessage();
                }
              }}
              placeholder={grillMode ? "Ceritakan ide atau rencana yang ingin di-stress-test…" : "Tulis pertanyaan atau konteks Anda…"}
              maxLength={12_000}
              disabled={loading}
              aria-label="Pesan"
            />
            <div className="composer-footer">
              <span className="composer-hint">Enter untuk kirim · Shift+Enter untuk baris baru</span>
              <button className="send-button" type="submit" disabled={loading || !input.trim()}>
                {loading ? "Mengirim…" : "Kirim"}
              </button>
            </div>
          </div>
        </form>
      </main>
    </div>
  );
}
