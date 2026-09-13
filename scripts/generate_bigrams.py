#!/usr/bin/env python3
"""
Bengali Bi-Gram Next-Word Extractor & Binary Compiler for OsthirKeyboard
Processes multi-domain Bengali sentence datasets, cleans orthography,
calculates transition frequencies P(W2 | W1), and compiles into an ultra-fast
compact binary index (bn_bigrams.bin).
"""

import os
import sys
import json
import struct
import re
import unicodedata
from collections import defaultdict, Counter
from pathlib import Path

# Ensure UTF-8 stdout
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_SENTENCES_DIR = ROOT_DIR / "raw_data_sources" / "bangla" / "sentences"
if not RAW_SENTENCES_DIR.exists():
    RAW_SENTENCES_DIR = ROOT_DIR / "raw_data_sources" / "sentences"
SOURCES_DIR = ROOT_DIR / "sources"
OUTPUT_DIR = ROOT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SOURCES_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_TXT = SOURCES_DIR / "bangla_bigrams.txt"
OUTPUT_BIN = OUTPUT_DIR / "bn_bigrams.bin"

# Bengali vowel signs (kars) & diacritics
BENGALI_KARS = set('\u09be\u09bf\u09c0\u09c1\u09c2\u09c3\u09c7\u09c8\u09cb\u09cc\u09cd\u0981\u0982\u0983')
# Sentence split delimiters
SENTENCE_SPLIT_REGEX = re.compile(r'[\।\?\!\,\;\:\n\r\t\(\)\[\]\{\}\"\'\“\”\—\-\–\/\<\>\=\+\*\#\@\$\%\^\&\_]+')

# High-priority conversational seeds to guarantee instant conversational readiness
CONVERSATIONAL_SEEDS = [
    ("আমি", ["তোমাকে", "এখন", "করব", "যাব", "ভালো", "মনে", "আছি"]),
    ("তুমি", ["কেমন", "কোথায়", "কি", "কখন", "যাবে", "করছ", "আছো"]),
    ("আপনি", ["কেমন", "কোথায়", "কি", "কখন", "যাবেন", "করছেন", "আছেন"]),
    ("কেমন", ["আছো", "আছেন", "হলো", "লাগল", "কাটল"]),
    ("শুভ", ["সকাল", "রাত্রি", "জন্মদিন", "কামনা", "সন্ধ্যা", "কামনা"]),
    ("অনেক", ["ধন্যবাদ", "সুন্দর", "ভালো", "কষ্ট", "ভালোবাসা", "দিন"]),
    ("খুব", ["ভালো", "সুন্দর", "সুন্দর", "কষ্ট", "খুশি"]),
    ("ধন্যবাদ", ["ভাই", "আপনাকে", "তোমাকে", "অনেক", "প্রিয়"]),
    ("বাসায়", ["যাব", "পৌঁছে", "আছি", "এসো", "যাও"]),
    ("খাবার", ["খেয়েছ", "খাব", "দাও", "খাই"]),
    ("কি", ["খবর", "করছ", "করছেন", "হয়েছে", "অবস্থা"]),
    ("কোথায়", ["আছো", "আছেন", "যাবে", "যাবেন"]),
    ("ইনশাআল্লাহ", ["ভালো", "হবে", "যাব", "দেখা"]),
    ("মাশাল্লাহ", ["অনেক", "সুন্দর", "ভালো"]),
    ("আলহামদুলিল্লাহ", ["ভালো", "আছি", "সব"]),
    ("দেখা", ["হবে", "করব", "করবেন", "হলে"]),
    ("কথা", ["বলব", "বলবেন", "হবে", "আছে"]),
    ("ভালো", ["থাকবেন", "থাকো", "লাগল", "হয়েছে"]),
    ("কখন", ["আসবে", "আসবেন", "যাবে", "হবে"]),
    ("আজ", ["সারাদিন", "বৃষ্টি", "রাতে", "সকালে"]),
    ("কাল", ["দেখা", "হবে", "যাব", "আসবে"]),
    ("কাজ", ["শেষ", "করছি", "করব", "আছে"]),
    ("টাকা", ["দাও", "পাঠাও", "আছে", "দিয়েছি"]),
    ("নাম্বার", ["দাও", "দিন", "পাঠাও"]),
    ("ফোন", ["দিচ্ছি", "দাও", "করব", "ধরো"]),
    ("মেসেজ", ["দাও", "করব", "দিয়েছি", "পেয়েছি"]),
]

def normalize_bengali(text: str) -> str:
    """Canonical Unicode normalization and nukta recomposition."""
    t = unicodedata.normalize('NFC', text.strip())
    # Recompose separated nuktas
    t = t.replace('\u09a1\u09bc', '\u09dc')  # ড + ় -> ড়
    t = t.replace('\u09a2\u09bc', '\u09dd')  # ঢ + ় -> ঢ়
    t = t.replace('\u09af\u09bc', '\u09df')  # য + ় -> য়
    # Strip zero-width joiner / non-joiner & byte order mark
    t = t.replace('\u200c', '').replace('\u200d', '').replace('\ufeff', '')
    return t

def is_valid_bengali_word(word: str) -> bool:
    """Validate orthographic structure of a single Bengali word."""
    if not word or len(word) < 1 or len(word) > 25:
        return False
    # Must only contain Bengali Unicode codepoints (U+0980 to U+09FF)
    for ch in word:
        code = ord(ch)
        if not (0x0980 <= code <= 0x09FF):
            return False
        # No digits
        if 0x09E6 <= code <= 0x09EF:
            return False
    # Cannot start with a dependent vowel sign (kar) or diacritic
    if word[0] in BENGALI_KARS:
        return False
    # Cannot end with a trailing virama (hasanta)
    if word[-1] == '\u09cd':
        return False
    # Cannot have consecutive vowel signs
    for i in range(len(word) - 1):
        if word[i] in BENGALI_KARS and word[i+1] in BENGALI_KARS:
            # Allow hasanta (্) or candrabindu (ঁ) combinations, but disallow adjacent full vowel kars
            if word[i] != '\u09cd' and word[i+1] != '\u09cd' and word[i+1] != '\u0981':
                return False
    return True

def extract_sentences_from_json(file_path: Path):
    """Extract sentence strings from JSON datasets (Alpaca, BanglaRQA)."""
    sentences = []
    print(f"[*] Parsing JSON: {file_path.name}...")
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    for k in ['instruction', 'input', 'output', 'context', 'question', 'answer', 'text']:
                        if k in item and isinstance(item[k], str):
                            sentences.append(item[k])
                elif isinstance(item, str):
                    sentences.append(item)
        elif isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, str):
                    sentences.append(v)
                elif isinstance(v, list):
                    for sub in v:
                        if isinstance(sub, dict):
                            for sk in ['context', 'question', 'text', 'title']:
                                if sk in sub and isinstance(sub[sk], str):
                                    sentences.append(sub[sk])
    except Exception as e:
        print(f"[-] Error reading {file_path.name}: {e}")
    return sentences

def extract_sentences_from_csv(file_path: Path):
    """Extract sentences and multi-word phrases from CSV files."""
    sentences = []
    print(f"[*] Parsing CSV: {file_path.name}...")
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parts = line.split(';')
                if len(parts) >= 3:
                    sentences.append(parts[2])
    except Exception as e:
        print(f"[-] Error reading {file_path.name}: {e}")
    return sentences

def build_bigrams():
    print("=" * 60)
    print("  Bengali Bi-Gram Dataset Builder & Compiler")
    print("=" * 60)

    raw_text_blocks = []

    # 1. Ingest JSON files
    for json_file in RAW_SENTENCES_DIR.glob("*.json"):
        if json_file.stat().st_size > 1000:
            raw_text_blocks.extend(extract_sentences_from_json(json_file))

    # 2. Ingest CSV files
    csv_file = ROOT_DIR / "raw_data_sources" / "bangla" / "BengaliDictionary_93..csv"
    if not csv_file.exists():
        csv_file = ROOT_DIR / "raw_data_sources" / "BengaliDictionary_93..csv"
    if csv_file.exists():
        raw_text_blocks.extend(extract_sentences_from_csv(csv_file))

    print(f"[+] Total raw sentence blocks collected: {len(raw_text_blocks):,}")

    # 3. Tokenize sentences and count transitions
    print("[*] Tokenizing sentences and calculating bigram transitions...")
    bigram_counts = defaultdict(Counter)
    unigram_counts = Counter()

    for block in raw_text_blocks:
        # Split block into sentences
        sentences = SENTENCE_SPLIT_REGEX.split(block)
        for s in sentences:
            s_clean = normalize_bengali(s)
            raw_words = s_clean.split()
            valid_words = [w for w in raw_words if is_valid_bengali_word(w)]
            if len(valid_words) < 2:
                continue
            for i in range(len(valid_words) - 1):
                w1 = valid_words[i]
                w2 = valid_words[i + 1]
                bigram_counts[w1][w2] += 1
                unigram_counts[w1] += 1

    # 4. Inject High-Priority Conversational Seeds
    print("[*] Injecting conversational seeds...")
    for w1, succs in CONVERSATIONAL_SEEDS:
        w1_norm = normalize_bengali(w1)
        for rank, w2 in enumerate(succs):
            w2_norm = normalize_bengali(w2)
            # Add artificial high count for top seeds
            bigram_counts[w1_norm][w2_norm] += (1000 - rank * 50)
            unigram_counts[w1_norm] += 1000

    print(f"[+] Distinct antecedent words with successors: {len(bigram_counts):,}")

    # 5. Prune and select top 3-5 successors per word
    print("[*] Pruning and ranking top next-word transitions...")
    final_bigrams = {}
    for w1, succ_map in bigram_counts.items():
        # Only keep words with meaningful usage (or seed words)
        total_occurrences = unigram_counts[w1]
        if total_occurrences < 2 and len(succ_map) < 2:
            continue
        # Sort successors by frequency descending
        top_succs = [w2 for w2, count in succ_map.most_common(5) if w2 != w1]
        if top_succs:
            final_bigrams[w1] = top_succs

    print(f"[+] Final curated vocabulary entries with predictions: {len(final_bigrams):,}")

    # 6. Save human-readable text file
    print(f"[*] Writing text file to {OUTPUT_TXT}...")
    with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
        f.write("# Bengali Bi-gram Next-Word Dataset (Antecedent -> Predicted Next Words)\n")
        for w1 in sorted(final_bigrams.keys()):
            succs_str = ",".join(final_bigrams[w1])
            f.write(f"{w1}\t{succs_str}\n")
    print(f"[+] Saved {OUTPUT_TXT} ({OUTPUT_TXT.stat().st_size:,} bytes)")

    # 7. Compile into Ultra-Compact Binary Format (bn_bigrams.bin)
    print(f"[*] Compiling compact binary index to {OUTPUT_BIN}...")
    compile_binary(final_bigrams, OUTPUT_BIN)

def compile_binary(bigrams_dict: dict, bin_path: Path):
    """
    Binary Layout for bn_bigrams.bin:
    
    Header (16 bytes):
      [0..3]   Magic: b'BGBN'
      [4..5]   Version: uint16 (1)
      [6..9]   Total Entries Count: uint32 (N)
      [10..13] Index Table Offset: uint32
      [14..15] Reserved: uint16 (0)
      
    Index Table (N * 12 bytes, sorted by w1 UTF-8 byte order):
      [0..3]   w1_offset (uint32 offset in String Pool)
      [4..7]   succ_list_offset (uint32 offset in Successors Array)
      [8..9]   succ_count (uint16 count of predicted next words)
      [10..11] reserved (uint16)
      
    Successor Offset Array (Total Successors * 4 bytes):
      Array of uint32 offsets in String Pool for each successor word
      
    String Pool:
      Concatenated UTF-8 null-terminated strings: word1\0word2\0...
    """
    # 1. Collect and deduplicate all unique words for the string pool
    string_pool = bytearray()
    string_offset_map = {}

    def get_string_offset(word: str) -> int:
        if word not in string_offset_map:
            offset = len(string_pool)
            encoded = word.encode('utf-8') + b'\x00'
            string_pool.extend(encoded)
            string_offset_map[word] = offset
        return string_offset_map[word]

    # Pre-populate string pool for all antecedents and successors
    sorted_antecedents = sorted(bigrams_dict.keys(), key=lambda w: w.encode('utf-8'))
    
    # 2. Build Successor Array & Index Table
    index_entries = []
    succ_array = []
    
    for w1 in sorted_antecedents:
        succs = bigrams_dict[w1]
        w1_off = get_string_offset(w1)
        succ_list_off = len(succ_array)
        for w2 in succs:
            w2_off = get_string_offset(w2)
            succ_array.append(w2_off)
        index_entries.append((w1_off, succ_list_off, len(succs)))

    # 3. Calculate Section Offsets
    header_size = 24
    index_table_offset = header_size
    index_table_size = len(index_entries) * 12
    succ_array_offset = index_table_offset + index_table_size
    succ_array_size = len(succ_array) * 4
    string_pool_offset = succ_array_offset + succ_array_size

    # 4. Pack Binary
    out_buf = bytearray()
    # Header (24 bytes)
    out_buf.extend(b'BGBN')                                    # 0..3 Magic
    out_buf.extend(struct.pack('<H', 1))                       # 4..5 Version 1
    out_buf.extend(struct.pack('<H', 0))                       # 6..7 Reserved
    out_buf.extend(struct.pack('<I', len(index_entries)))       # 8..11 Total entries
    out_buf.extend(struct.pack('<I', index_table_offset))       # 12..15 Index Table Offset
    out_buf.extend(struct.pack('<I', succ_array_offset))       # 16..19 Succ Array Offset
    out_buf.extend(struct.pack('<I', string_pool_offset))      # 20..23 String Pool Offset

    # Index Table
    for w1_off, succ_off, count in index_entries:
        out_buf.extend(struct.pack('<IIHH', w1_off, succ_off, count, 0))

    # Successor Array
    for succ_w_off in succ_array:
        out_buf.extend(struct.pack('<I', succ_w_off))

    # String Pool
    out_buf.extend(string_pool)

    # Write to file
    with open(bin_path, 'wb') as f:
        f.write(out_buf)

    print(f"[+] Successfully compiled {bin_path.name}:")
    print(f"    - Total Antecedents (Index Table): {len(index_entries):,}")
    print(f"    - Total Successor Pointers: {len(succ_array):,}")
    print(f"    - Unique Strings in Pool: {len(string_offset_map):,}")
    print(f"    - Total Binary File Size: {len(out_buf):,} bytes ({len(out_buf)/1024/1024:.2f} MB)")

if __name__ == "__main__":
    build_bigrams()
