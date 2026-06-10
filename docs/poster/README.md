# MentorMinds — DIGITEX 2026 e-poster (comic edition)

Comic-book style: Bangers display lettering, thick black outlines, a BANG
burst callout, halftone dots, hard sticker shadows.

## Files
- **MentorMinds-DIGITEX2026-poster.pptx** — A1 portrait on the official
  DIGITEX 2026 template frame (submit / print this).
- **MentorMinds-DIGITEX2026-poster.png** — 2245×3179 static raster.
- **poster.html** — source. **Open in a browser for the ANIMATED version**
  (floating phone, bobbing feature chips, typing dots, pulsing BANG burst,
  filling mastery bar, falling confetti). Add `?static=1` to freeze it.
- **render.mjs** — re-render the static PNG: `node render.mjs` (needs
  Playwright Chromium; symlink ../../frontend/node_modules first).

## Design notes
A real MentorMinds app screen is the hero (the tutor solving 2x+3=11
grounded in a 9709 mark scheme, an adaptive quiz, the mastery bar), real
product features as comic sticker callouts, real stats ($0 API keys is the
genuine differentiator). Follows award-poster conventions: 3-30-300 rule,
~60% visual / 40% text, bold hierarchy.
