export function redact(text: string): string {
  let value = text.replace(
    /(authorization\s*[:=]\s*)(bearer\s+)?[^\s,;]+/gi,
    (_match, prefix: string, scheme?: string) => prefix + (scheme ?? "") + "[REDACTED]"
  );
  value = value.replace(
    /\b(password|passwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|client_secret)\b(\s*[:=]\s*)(['"]?)[^\s,;'"}]+\3/gi,
    (_match, name: string, separator: string, quote: string) =>
      name + separator + quote + "[REDACTED]" + quote
  );
  value = value.replace(/\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/g, "[REDACTED]");
  value = value.replace(/[\w.+-]+@[\w-]+\.[\w.-]+/g, "[EMAIL]");
  return value;
}
