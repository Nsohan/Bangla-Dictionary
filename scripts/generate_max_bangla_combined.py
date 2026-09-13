#!/usr/bin/env python3
"""
Pipeline to aggregate, clean, validate, score, and generate the maximum
valid Bangla dictionary for OsthirKeyboard (AOSP .combined format).
"""

import re
import unicodedata
import sys
from pathlib import Path
from typing import Dict, Set, Tuple

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent.parent
SOURCES_DIR = ROOT_DIR / "sources"
RAW_DIR = ROOT_DIR / "raw_data_sources" / "bangla"
if not RAW_DIR.exists():
    RAW_DIR = ROOT_DIR / "raw_data_sources"
OUTPUT_COMBINED = SOURCES_DIR / "bangla_words.combined"

# Bengali character pattern
BENGALI_CHAR_PATTERN = re.compile(r'^[\u0980-\u09FF]+$')

# Dependent vowel signs and diacritics that cannot start a word
INVALID_START_CHARS = set(
    '\u09be\u09bf\u09c0\u09c1\u09c2\u09c3\u09c4\u09c7\u09c8\u09cb\u09cc'  # kārs
    '\u09cd'  # virama / hasanta
    '\u0981\u0982\u0983'  # chandrabindu, anusvara, visarga
    '\u09bc'  # nukta
)

KARS_STR = '\u09be\u09bf\u09c0\u09c1\u09c2\u09c3\u09c4\u09c7\u09c8\u09cb\u09cc'
CONSECUTIVE_KAR_PATTERN = re.compile(f'[{KARS_STR}][{KARS_STR}]')
CONSECUTIVE_HASANTA_PATTERN = re.compile(r'\u09cd\u09cd')

def clean_and_normalize(token: str) -> str:
    """Normalize Unicode, recompose Bengali nuktas, and strip legacy ZWJ/ZWNJ artifacts and punctuation."""
    # Strip zero-width non-joiner and joiner which break modern Unicode keyboards
    cleaned = token.replace('\u200c', '').replace('\u200d', '')
    # Normalize NFC
    cleaned = unicodedata.normalize('NFC', cleaned.strip())
    # Recompose Bengali nukta characters that Unicode NFC leaves decomposed
    cleaned = cleaned.replace('\u09a1\u09bc', '\u09dc')  # ড + ় -> ড় (U+09DC)
    cleaned = cleaned.replace('\u09a2\u09bc', '\u09dd')  # ঢ + ় -> ঢ় (U+09DD)
    cleaned = cleaned.replace('\u09af\u09bc', '\u09df')  # য + ় -> য় (U+09DF)
    # Strip leading/trailing symbols, punctuation, quotes, brackets
    cleaned = cleaned.strip(' \t\r\n.,;:!?"\'`()[]{}<>-–—/\\|*&#@~^+=_')
    return cleaned

def is_valid_bangla_word(w: str) -> bool:
    """Rigorous phonetic and orthographic validation for modern Bengali words."""
    if not w or len(w) < 1 or len(w) > 20:
        return False
    # Must only contain Bengali script
    if not BENGALI_CHAR_PATTERN.match(w):
        return False
    # Cannot start with a dependent vowel sign or diacritic
    if w[0] in INVALID_START_CHARS:
        return False
    # Cannot end with a trailing virama / hasanta (signals truncated words)
    if w.endswith('\u09cd'):
        return False
    # Cannot have consecutive vowel signs
    if CONSECUTIVE_KAR_PATTERN.search(w):
        return False
    # Cannot have consecutive viramas
    if CONSECUTIVE_HASANTA_PATTERN.search(w):
        return False
    # Reject pure numeric digit strings (e.g. '১২৩৪')
    if all('\u09e6' <= c <= '\u09ef' for c in w):
        return False
    return True

def load_existing_baseline() -> Dict[str, int]:
    """Load hand-tuned baseline frequencies from current bangla_words.combined."""
    baseline = {}
    if OUTPUT_COMBINED.exists():
        with open(OUTPUT_COMBINED, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('word='):
                    parts = line.split(',')
                    w = parts[0][5:]
                    freq = 200
                    for p in parts[1:]:
                        if p.startswith('f='):
                            try:
                                freq = int(p[2:])
                            except ValueError:
                                pass
                    baseline[w] = freq
    print(f"[+] Loaded {len(baseline)} hand-tuned baseline words from existing bangla_words.combined")
    return baseline

def load_occurrence_ranks() -> Dict[str, int]:
    """
    Extract ranking from Bangla_word_list_highest_to_lowest_occurs.txt.
    Only keeps clean, valid Bengali words to avoid corrupted virama-stripped tokens.
    """
    ranks = {}
    rank_file = RAW_DIR / "Bangla_word_list_highest_to_lowest_occurs.txt"
    if not rank_file.exists():
        return ranks
    
    print("[*] Ingesting occurrence rankings...")
    rank = 0
    with open(rank_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            w = clean_and_normalize(line)
            if not is_valid_bangla_word(w):
                continue
            rank += 1
            if w not in ranks:
                ranks[w] = rank
    print(f"[+] Extracted occurrence rankings for {len(ranks)} valid words")
    return ranks

def main():
    print("=" * 65)
    print("  Bangla Maximum Vocabulary Generator & Orthographic Validator")
    print("=" * 65)

    baseline_freqs = load_existing_baseline()
    occurrence_ranks = load_occurrence_ranks()

    # Dictionary of word -> set of sources it appears in
    word_sources: Dict[str, Set[str]] = {}

    sources = [
        ("Bangla_root_word.txt", "line"),
        ("BengaliDictionary_93..csv", "csv"),
        ("BengaliWordList_40.txt", "line"),
        ("BengaliWordList_48.txt", "line"),
        ("BengaliWordList_112.txt", "line"),
        ("BengaliWordList_439.txt", "line"),
        ("bangla_number.txt", "line"),
    ]

    for fname, ftype in sources:
        fpath = RAW_DIR / fname
        if not fpath.exists():
            print(f"[-] Warning: Source not found: {fpath}")
            continue

        count = 0
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                candidates = []
                if ftype == "csv":
                    parts = line.split(';')
                    if len(parts) >= 3:
                        raw_trans = parts[2].replace('/', ' ').replace(',', ' ').replace('(', ' ').replace(')', ' ')
                        candidates = raw_trans.split()
                else:
                    candidates = line.split()

                for c in candidates:
                    word = clean_and_normalize(c)
                    if is_valid_bangla_word(word):
                        if word not in word_sources:
                            word_sources[word] = set()
                        word_sources[word].add(fname)
                        count += 1
        print(f"[+] Loaded {fname}: {count} valid occurrences")

    # Also ensure baseline words are in word_sources
    for w in baseline_freqs:
        clean_w = clean_and_normalize(w)
        if is_valid_bangla_word(clean_w):
            if clean_w not in word_sources:
                word_sources[clean_w] = set()
            word_sources[clean_w].add("baseline")

    total_unique = len(word_sources)
    print(f"\n[+] Total unique validated Bengali words: {total_unique:,}")

    # Compute frequencies
    final_entries = []
    for word, srcs in word_sources.items():
        if word in baseline_freqs:
            freq = baseline_freqs[word]
        else:
            n_src = len(srcs)
            # Base frequency by source corroboration
            if n_src >= 5:
                freq = 190
            elif n_src == 4:
                freq = 165
            elif n_src == 3:
                freq = 140
            elif n_src == 2:
                freq = 110
            else:
                freq = 70

            # Boost with real-world occurrence rank if available
            if word in occurrence_ranks:
                r = occurrence_ranks[word]
                if r <= 500:
                    freq = max(freq, 245)
                elif r <= 1500:
                    freq = max(freq, 235)
                elif r <= 5000:
                    freq = max(freq, 220)
                elif r <= 15000:
                    freq = max(freq, 195)
                elif r <= 40000:
                    freq = max(freq, 165)
                elif r <= 80000:
                    freq = max(freq, 135)
                elif r <= 150000:
                    freq = max(freq, 105)

        freq = min(max(freq, 1), 255)
        final_entries.append((word, freq))

    # Sort entries by frequency descending, then lexicographically by UTF-8 bytes ascending
    print("[*] Sorting dictionary entries...")
    final_entries.sort(key=lambda item: (-item[1], item[0].encode('utf-8')))

    # Write output bangla_words.combined
    print(f"[*] Writing to {OUTPUT_COMBINED}...")
    with open(OUTPUT_COMBINED, 'w', encoding='utf-8') as f:
        f.write("dictionary=main:bn,description=Bengali High Frequency Vocabulary,locale=bn,date=1700000000,version=2\n")
        for word, freq in final_entries:
            f.write(f"word={word},f={freq}\n")

    out_size = OUTPUT_COMBINED.stat().st_size
    print(f"[✓] Successfully generated {OUTPUT_COMBINED}")
    print(f"    Total words: {len(final_entries):,}")
    print(f"    File size: {out_size:,} bytes ({out_size / 1024 / 1024:.2f} MB)")

    # Print frequency distribution
    freq_tiers = {
        "220 - 255 (Top tier)": 0,
        "180 - 219 (Very frequent)": 0,
        "140 - 179 (Common)": 0,
        "100 - 139 (Standard)": 0,
        " 50 -  99 (Extended/Inflections)": 0,
        "  1 -  49 (Rare)": 0,
    }
    for _, freq in final_entries:
        if freq >= 220:
            freq_tiers["220 - 255 (Top tier)"] += 1
        elif freq >= 180:
            freq_tiers["180 - 219 (Very frequent)"] += 1
        elif freq >= 140:
            freq_tiers["140 - 179 (Common)"] += 1
        elif freq >= 100:
            freq_tiers["100 - 139 (Standard)"] += 1
        elif freq >= 50:
            freq_tiers[" 50 -  99 (Extended/Inflections)"] += 1
        else:
            freq_tiers["  1 -  49 (Rare)"] += 1

    print("\nFrequency Distribution:")
    for tier, count in freq_tiers.items():
        print(f"  {tier}: {count:>8,} words ({count/len(final_entries)*100:>5.1f}%)")

if __name__ == "__main__":
    main()
