#!/usr/bin/env python3
"""Subject-agnostic past-paper fetcher.

Downloads Cambridge question-paper / mark-scheme pairs from a public
mirror into data/papers/, ready for the alignment pipeline.

Instead of guessing paper variants, each subject's per-year listing
page (e.g. .../mathematics-9709/2022/summer.php) is scraped for the
exact qp/ms files the mirror hosts, then each PDF is downloaded
directly. That removes 404 retry storms and catches every variant.

Usage:
    python scripts/fetch_papers.py                 # all configured subjects
    python scripts/fetch_papers.py 4024 0580       # only these codes
    python scripts/fetch_papers.py --years 2021 2022 2023

Papers are © UCLES; use for personal/educational model training only.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.request
from pathlib import Path

MIRROR = "https://bestexamhelp.com/exam"
DEST = Path(__file__).resolve().parent.parent / "data" / "papers"

# (syllabus_code, level_slug, subject_slug) — verified against the
# mirror's index pages. Pure first/second-language syllabi and
# performance subjects (art, drama, music) are omitted: QP/MS
# alignment is meaningless there, so they would only add noise.
SUBJECTS: list[tuple[str, str, str]] = [
    # --- Cambridge O Level ---
    ("4024", "cambridge-o-level", "mathematics-d-4024"),
    ("4037", "cambridge-o-level", "mathematics-additional-4037"),
    ("4040", "cambridge-o-level", "statistics-4040"),
    ("5054", "cambridge-o-level", "physics-5054"),
    ("5070", "cambridge-o-level", "chemistry-5070"),
    ("5090", "cambridge-o-level", "biology-5090"),
    ("2281", "cambridge-o-level", "economics-2281"),
    ("2210", "cambridge-o-level", "computer-science-2210"),
    ("7010", "cambridge-o-level", "computer-studies-7010"),
    ("7115", "cambridge-o-level", "business-studies-7115"),
    ("7707", "cambridge-o-level", "accounting-7707"),
    ("7110", "cambridge-o-level", "principles-of-accounts-7110"),
    ("7100", "cambridge-o-level", "commerce-7100"),
    ("2059", "cambridge-o-level", "pakistan-studies-2059"),
    ("7094", "cambridge-o-level", "bangladesh-studies-7094"),
    # --- Cambridge IGCSE ---
    ("0452", "cambridge-igcse", "accounting-0452"),
    ("0600", "cambridge-igcse", "agriculture-0600"),
    ("0610", "cambridge-igcse", "biology-0610"),
    ("0450", "cambridge-igcse", "business-studies-0450"),
    ("0620", "cambridge-igcse", "chemistry-0620"),
    ("0478", "cambridge-igcse", "computer-science-0478"),
    ("0455", "cambridge-igcse", "economics-0455"),
    ("0475", "cambridge-igcse", "english-literature-0475"),
    ("0454", "cambridge-igcse", "enterprise-0454"),
    ("0680", "cambridge-igcse", "environmental-management-0680"),
    ("0648", "cambridge-igcse", "food-and-nutrition-0648"),
    ("0460", "cambridge-igcse", "geography-0460"),
    ("0457", "cambridge-igcse", "global-perspectives-0457"),
    ("0470", "cambridge-igcse", "history-0470"),
    ("0493", "cambridge-igcse", "islamiyat-0493"),
    ("0580", "cambridge-igcse", "mathematics-0580"),
    ("0606", "cambridge-igcse", "mathematics-additional-0606"),
    ("0607", "cambridge-igcse", "mathematics-international-0607"),
    ("0413", "cambridge-igcse", "physical-education-0413"),
    ("0625", "cambridge-igcse", "physics-0625"),
    ("0490", "cambridge-igcse", "religious-studies-0490"),
    ("0653", "cambridge-igcse", "science-combined-0653"),
    ("0654", "cambridge-igcse", "sciences-co-ordinated-0654"),
    ("0495", "cambridge-igcse", "sociology-0495"),
    ("0471", "cambridge-igcse", "travel-and-tourism-0471"),
    # --- Cambridge International AS & A Level ---
    ("9709", "cambridge-international-a-level", "mathematics-9709"),
    ("9231", "cambridge-international-a-level", "mathematics-further-9231"),
    ("9702", "cambridge-international-a-level", "physics-9702"),
    ("9701", "cambridge-international-a-level", "chemistry-9701"),
    ("9700", "cambridge-international-a-level", "biology-9700"),
    ("9708", "cambridge-international-a-level", "economics-9708"),
    ("9618", "cambridge-international-a-level", "computer-science-9618"),
    ("9608", "cambridge-international-a-level", "computer-science-9608"),
    ("9691", "cambridge-international-a-level", "computing-9691"),
    ("9706", "cambridge-international-a-level", "accounting-9706"),
    ("9609", "cambridge-international-a-level", "business-9609"),
    ("9707", "cambridge-international-a-level", "business-studies-9707"),
    ("9990", "cambridge-international-a-level", "psychology-9990"),
    ("9698", "cambridge-international-a-level", "psychology-9698"),
    ("9699", "cambridge-international-a-level", "sociology-9699"),
    ("9489", "cambridge-international-a-level", "history-9489"),
    ("9488", "cambridge-international-a-level", "islamic-studies-9488"),
    ("9084", "cambridge-international-a-level", "law-9084"),
]

DEFAULT_YEARS = [str(y) for y in range(2017, 2026)]
SESSIONS = [("s", "summer"), ("w", "winter")]

# href="9709-s22-qp-41.php" on a year listing page
LISTING_RE = re.compile(
    r'href="(\d{4})-([swm]\d{2})-(qp|ms)-(\w{1,2})\.php"'
)


def http_get(url: str, timeout: int = 30) -> bytes | None:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except Exception:
        return None


def listing_files(level: str, slug: str, year: str, session_page: str) -> list[str]:
    """PDF filenames the mirror hosts for one subject/year/session."""
    page = http_get(f"{MIRROR}/{level}/{slug}/{year}/{session_page}.php", timeout=20)
    if not page:
        return []
    names = []
    for code, sess, doc, variant in LISTING_RE.findall(page.decode("utf-8", "ignore")):
        names.append(f"{code}_{sess}_{doc}_{variant}.pdf")
    return sorted(set(names))


def download(url: str, dest: Path, retries: int = 1) -> bool:
    for attempt in range(retries + 1):
        data = http_get(url)
        if data and data[:4] == b"%PDF":
            dest.write_bytes(data)
            return True
        if attempt < retries:
            time.sleep(2)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("codes", nargs="*", help="Only fetch these syllabus codes")
    parser.add_argument("--years", nargs="*", default=DEFAULT_YEARS)
    parser.add_argument("--throttle", type=float, default=0.5)
    args = parser.parse_args()

    DEST.mkdir(parents=True, exist_ok=True)
    subjects = [s for s in SUBJECTS if not args.codes or s[0] in args.codes]

    got = missing = 0
    for code, level, slug in subjects:
        subject_got = 0
        for year in args.years:
            for _, session_page in SESSIONS:
                names = listing_files(level, slug, year, session_page)
                time.sleep(args.throttle)
                for name in names:
                    target = DEST / name
                    if target.exists():
                        continue
                    url = f"{MIRROR}/{level}/{slug}/{year}/{name}"
                    if download(url, target):
                        got += 1
                        subject_got += 1
                    else:
                        missing += 1
                    time.sleep(args.throttle)
        print(f"{code} {slug}: +{subject_got} files", flush=True)

    print(f"\nDownloaded {got} new files ({missing} not available).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
