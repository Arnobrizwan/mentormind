# MentorMinds — DIGITEX 2026 e-poster (comic edition)

Comic-book style (Bangers/Unbounded lettering, thick black outlines, halftone
dots, hard sticker shadows) organised into five numbered, judge-friendly
panels: **1 Problem · 2 Why It's Different · 3 AI Under the Hood ·
4 Evidence & Impact · 5 UN SDG Alignment**, with a live-app phone hero and a
scannable QR code to the repo.

## Files
- **MentorMinds-DIGITEX2026-poster.pptx** — A1 portrait (594×841 mm), the new
  PNG wrapped full-bleed (submit / print this; one flat image, not editable).
- **MentorMinds-DIGITEX2026-editable.pptx** — A1 portrait with **real, editable
  text boxes + shapes** for Canva / PowerPoint (import this to edit). The
  UTM/DIGITEX frame is a background image and the phone is `phone.png`; comic
  effects, custom fonts and animations do not carry over. Build with
  `node render.mjs && node render_phone.mjs && python build_editable_pptx.py`.
- **MentorMinds-DIGITEX2026-poster.png** — 2245×3179 static raster.
- **poster.html** — source. **Open in a browser for the ANIMATED version**
  (floating phone, typing dots, filling progress bar, falling confetti).
  Add `?static=1` to freeze it.
- **qr.png** — QR code → https://github.com/Arnobrizwan/mentormind. Regenerate
  with `npx qrcode -o qr.png -w 600 "https://github.com/Arnobrizwan/mentormind"`.
- **render.mjs** — re-render the static PNG: `node render.mjs` (needs Playwright
  Chromium; symlink `../../frontend/node_modules` first, then delete it after).
- **build_pptx.py** — wrap the PNG into the A1 .pptx:
  `pip install python-pptx && python build_pptx.py`.

## Accuracy
Every claim is grounded in the codebase (verified against `backend/apps/tutor`,
`ml-service`, and the Angular apps): mark-scheme **retrieval** over 1,521
Cambridge past-paper documents / 1,142 Q&A pairs across 20 subjects, an optional
LoRA fine-tune, OpenCV proctoring/OMR + Tesseract OCR, a dropout-risk model
(DVC + MLflow), and gamification — all self-hosted with **no third-party AI
APIs**. Not-yet-shipped ideas (Voice Tutor, Snap & Solve, adaptive/mastery
quizzes, offline mode, Bahasa) are intentionally **not** claimed.

## Design notes
Follows award-poster conventions: bold hierarchy, ~60% visual / 40% text, a real
app screen as the hero, real product features, and measurable evidence.
