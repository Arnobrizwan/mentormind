/** Minimal, safe markdown → HTML (escape-first, no raw HTML). */
export function renderMarkdown(text: string): string {
  const escaped = text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
  const lines = escaped.split('\n').map((line) => {
    let out = line;
    if (/^\s*&gt;\s?/.test(out)) {
      out = `<blockquote class="md-quote">${out.replace(/^\s*&gt;\s?/, '')}</blockquote>`;
    } else if (/^\s*[-*+]\s+/.test(out)) {
      out = `<span class="md-li">${out.replace(/^\s*[-*+]\s+/, '• ')}</span>`;
    } else if (/^\s*\d+\.\s+/.test(out)) {
      out = `<span class="md-ol">${out}</span>`;
    }
    return out;
  });
  let html = lines.join('<br>');
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/(^|[\s>])_([^_]+)_(?=[\s<.,!?)]|$)/g, '$1<em>$2</em>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  return html;
}

/** Split tutor replies into body + Cambridge mark-scheme citation. */
export function parseTutorReply(content: string): { body: string; source: string | null } {
  const divider = '\n\n---\n';
  const idx = content.indexOf(divider);
  if (idx < 0) return { body: content, source: null };
  const tail = content.slice(idx + divider.length).trim();
  const match = tail.match(/\*Source:\s*([^*]+)\*/);
  return {
    body: content.slice(0, idx).trimEnd(),
    source: match ? match[1].trim() : tail.replace(/^\*|\*$/g, '').trim() || null,
  };
}
