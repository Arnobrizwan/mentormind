import { describe, expect, it } from 'vitest';

import { renderMarkdown } from './markdown';

describe('renderMarkdown math support', () => {
  it('renders $inline$ TeX through KaTeX', () => {
    const html = renderMarkdown('Solve $x^2 + 1 = 0$ for x.');
    expect(html).toContain('katex');
    expect(html).not.toContain('$x^2');
  });

  it('renders $$display$$ TeX in display mode', () => {
    const html = renderMarkdown('$$\\frac{a}{b}$$');
    expect(html).toContain('katex-display');
  });

  it('leaves money amounts alone', () => {
    const html = renderMarkdown('The book costs $5 and the pen costs $2.');
    expect(html).not.toContain('katex');
    expect(html).toContain('$5');
  });

  it('still escapes HTML outside math', () => {
    const html = renderMarkdown('<script>alert(1)</script> and $x$');
    expect(html).toContain('&lt;script&gt;');
    expect(html).toContain('katex');
  });

  it('keeps plain markdown working', () => {
    const html = renderMarkdown('**bold** and `code`');
    expect(html).toContain('<strong>bold</strong>');
    expect(html).toContain('<code>code</code>');
  });
});
