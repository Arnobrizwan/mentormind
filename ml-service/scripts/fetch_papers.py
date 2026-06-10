#!/usr/bin/env python3
"""Subject-agnostic past-paper fetcher.

Downloads Cambridge question-paper / mark-scheme pairs from a public
mirror into data/papers/, ready for the alignment pipeline. Covers any
subject in SUBJECTS — add a row to widen coverage.

Usage:
    python scripts/fetch_papers.py                 # all configured subjects
    python scripts/fetch_papers.py 4024 5070       # only these codes
    python scripts/fetch_papers.py --years 2021 2022 2023

Papers are © UCLES; use for personal/educational model training only.
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.request
from pathlib import Path

MIRROR = "https://bestexamhelp.com/exam"
DEST = Path(__file__).resolve().parent.parent / "data" / "papers"

# (syllabus_code, level_slug, subject_slug, [paper_variants])
# Every academic O Level subject from the Cambridge catalogue. Pure
# first/second-language papers (Arabic, Bengali, Urdu, Tamil, Sinhala,
# Setswana) are omitted: QP/MS alignment is meaningless for language
# comprehension/composition, so they would only add noise to training.
SUBJECTS: list[tuple[str, str, str, list[str]]] = [
    # --- Cambridge O Level — sciences & maths ---
    ("4024", "cambridge-o-level", "mathematics-d-4024", ["11", "12", "21", "22"]),
    ("4037", "cambridge-o-level", "mathematics-additional-4037", ["11", "12", "21", "22"]),
    ("4040", "cambridge-o-level", "statistics-4040", ["12", "13", "22", "23"]),
    ("5054", "cambridge-o-level", "physics-5054", ["11", "12", "21", "22"]),
    ("5070", "cambridge-o-level", "chemistry-5070", ["11", "12", "21", "22"]),
    ("5090", "cambridge-o-level", "biology-5090", ["11", "12", "21", "22"]),
    ("5129", "cambridge-o-level", "combined-science-5129", ["11", "12", "21", "22"]),
    ("5038", "cambridge-o-level", "agriculture-5038", ["12", "22"]),
    ("5014", "cambridge-o-level", "environmental-management-5014", ["12", "22"]),
    ("6065", "cambridge-o-level", "food-and-nutrition-6065", ["12", "22"]),
    # --- Cambridge O Level — commerce & social sciences ---
    ("2281", "cambridge-o-level", "economics-2281", ["12", "13", "22", "23"]),
    ("2210", "cambridge-o-level", "computer-science-2210", ["11", "12", "21", "22"]),
    ("7115", "cambridge-o-level", "business-studies-7115", ["12", "13", "22", "23"]),
    ("7707", "cambridge-o-level", "accounting-7707", ["12", "13", "22", "23"]),
    ("7100", "cambridge-o-level", "commerce-7100", ["12", "22"]),
    ("7096", "cambridge-o-level", "travel-and-tourism-7096", ["12", "22"]),
    ("2251", "cambridge-o-level", "sociology-2251", ["12", "13", "22", "23"]),
    ("2217", "cambridge-o-level", "geography-2217", ["12", "13", "22", "23"]),
    ("2147", "cambridge-o-level", "history-2147", ["12", "13"]),
    ("2069", "cambridge-o-level", "global-perspectives-2069", ["12", "13"]),
    # --- Cambridge O Level — humanities & religious studies ---
    ("2010", "cambridge-o-level", "literature-in-english-2010", ["12", "22"]),
    ("2055", "cambridge-o-level", "hinduism-2055", ["12", "22"]),
    ("2058", "cambridge-o-level", "islamiyat-2058", ["12", "22"]),
    ("2059", "cambridge-o-level", "pakistan-studies-2059", ["12", "22"]),
    ("2068", "cambridge-o-level", "islamic-studies-2068", ["12", "22"]),
    ("2035", "cambridge-o-level", "biblical-studies-2035", ["12", "22"]),
    ("7094", "cambridge-o-level", "bangladesh-studies-7094", ["12", "22"]),
    # --- Cambridge International AS & A Level (same pipeline) ---
    ("9709", "cambridge-international-a-level", "mathematics-9709", ["11", "12", "13"]),
    ("9702", "cambridge-international-a-level", "physics-9702", ["11", "12", "22"]),
    ("9701", "cambridge-international-a-level", "chemistry-9701", ["11", "12", "22"]),
    ("9700", "cambridge-international-a-level", "biology-9700", ["11", "12", "22"]),
    ("9708", "cambridge-international-a-level", "economics-9708", ["12", "13", "22"]),
    ("9618", "cambridge-international-a-level", "computer-science-9618", ["11", "12", "22"]),
    ("9706", "cambridge-international-a-level", "accounting-9706", ["12", "22"]),
    ("9609", "cambridge-international-a-level", "business-9609", ["12", "22"]),
    ("9990", "cambridge-international-a-level", "psychology-9990", ["12", "22"]),
    ("9389", "cambridge-international-a-level", "history-9389", ["12"]),
]

DEFAULT_YEARS = ["2021", "2022", "2023"]
SESSIONS = ["s", "w"]  # summer / winter


def two_digit(year: str) -> str:
    return year[-2:]


def download(url: str, dest: Path, retries: int = 2) -> bool:
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read()
            if data[:4] != b"%PDF":
                return False
            dest.write_bytes(data)
            return True
        except Exception:
            if attempt < retries:
                time.sleep(2)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("codes", nargs="*", help="Only fetch these syllabus codes")
    parser.add_argument("--years", nargs="*", default=DEFAULT_YEARS)
    parser.add_argument("--throttle", type=float, default=1.0)
    args = parser.parse_args()

    DEST.mkdir(parents=True, exist_ok=True)
    subjects = [s for s in SUBJECTS if not args.codes or s[0] in args.codes]

    got = missing = 0
    for code, level, slug, variants in subjects:
        subject_got = 0
        for year in args.years:
            for session in SESSIONS:
                for variant in variants:
                    stem = f"{code}_{session}{two_digit(year)}"
                    for doc in ("qp", "ms"):
                        name = f"{stem}_{doc}_{variant}.pdf"
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
