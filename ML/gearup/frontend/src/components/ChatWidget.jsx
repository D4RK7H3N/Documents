import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api, peso } from "../api.js";
import { useAuth } from "../context/AuthContext.jsx";

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hi! I'm the GearUp assistant. Ask me things like 'best keyboard under ₱3000' or 'recommend a gift for a gamer'.",
      products: [],
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);
  const location = useLocation();
  const { user } = useAuth();

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, loading, open]);

  const send = async (event) => {
    event.preventDefault();
    const message = input.trim();
    if (!message || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: message }]);
    setLoading(true);
    try {
      const data = await api("/chat/", {
        method: "POST",
        body: { message },
        auth: false,
      });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: data.answer, products: data.products || [] },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "error", text: err.message || "The assistant is unavailable." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label={open ? "Close assistant" : "Open AI assistant"}
        className="fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500 text-slate-950 shadow-lg shadow-emerald-900/40 transition hover:bg-emerald-400"
      >
        {open ? (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        )}
      </button>

      {open && (
        <div className="fixed bottom-24 right-5 z-50 flex h-[480px] w-[min(92vw,380px)] flex-col overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
          <div className="border-b border-slate-800 bg-slate-900 px-4 py-3">
            <p className="text-sm font-semibold">GearUp Assistant</p>
            <p className="text-xs text-slate-500">
              Answers from our catalog only
              {user ? "" : " · login to keep your history"}
            </p>
          </div>

          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.map((message, index) => (
              <div key={index} className={message.role === "user" ? "text-right" : ""}>
                <div
                  className={`inline-block max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                    message.role === "user"
                      ? "bg-emerald-500 text-slate-950"
                      : message.role === "error"
                        ? "border border-rose-900 bg-rose-950/60 text-rose-300"
                        : "bg-slate-800 text-slate-100"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{message.text}</p>
                </div>
                {message.products?.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {message.products.map((product) => (
                      <Link
                        key={product.slug}
                        to={`/products/${product.slug}`}
                        onClick={() => setOpen(false)}
                        className="rounded-full border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-emerald-300 transition hover:border-emerald-500"
                      >
                        {product.name} · {peso(product.price)}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="inline-flex items-center gap-1 rounded-2xl bg-slate-800 px-3 py-2">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:150ms]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:300ms]" />
              </div>
            )}
          </div>

          <form onSubmit={send} className="flex gap-2 border-t border-slate-800 p-3">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask about products…"
              aria-label="Message the assistant"
              className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none placeholder-slate-600 focus:border-emerald-500"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="rounded-xl bg-emerald-500 px-4 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:opacity-40"
            >
              Send
            </button>
          </form>
        </div>
      )}
    </>
  );
}
