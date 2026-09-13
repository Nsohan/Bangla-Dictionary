#!/usr/bin/env python3
"""
English Bi-Gram Next-Word Extractor & Binary Compiler for OsthirKeyboard / NHSCustomKeyboard.
Processes Web 1T (Norvig 2-words), Stanford Alpaca 52k conversation corpus,
and high-priority conversational seeds.
Calculates transition frequencies P(W2 | W1), and compiles into an ultra-fast
compact binary index (en_bigrams.bin).
"""

import os
import sys
import json
import struct
import re
import math
from collections import defaultdict, Counter
from pathlib import Path

# Ensure UTF-8 stdout
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_ENGLISH_DIR = ROOT_DIR / "raw_data_sources" / "english"
SOURCES_DIR = ROOT_DIR / "sources"
OUTPUT_DIR = ROOT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SOURCES_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_TXT = SOURCES_DIR / "en_bigrams.txt"
OUTPUT_BIN = OUTPUT_DIR / "en_bigrams.bin"

# Punctuation for sentence splitting
SENTENCE_SPLIT_REGEX = re.compile(r'[\.\?\!\;\:\n\r\t\(\)\[\]\{\}\"\—\–\/\<\>\=\+\*\#\@\$\%\^\&\_\\\|]+')

# Token matching: lowercase letters, with optional single apostrophe for contractions
WORD_REGEX = re.compile(r"^[a-z]+('[a-z]+)?$")

# Common contractions normalization map
CONTRACTION_MAP = {
    "dont": "don't",
    "cant": "can't",
    "wont": "won't",
    "im": "i'm",
    "youre": "you're",
    "theyre": "they're",
    "weve": "we've",
    "youve": "you've",
    "ive": "i've",
    "isnt": "isn't",
    "arent": "aren't",
    "wasnt": "wasn't",
    "werent": "weren't",
    "hasnt": "hasn't",
    "havent": "haven't",
    "hadnt": "hadn't",
    "doesnt": "doesn't",
    "couldnt": "couldn't",
    "shouldnt": "shouldn't",
    "wouldnt": "wouldn't",
    "didnt": "didn't",
    "that's": "that's",
    "thats": "that's",
    "what's": "what's",
    "whats": "what's",
    "it's": "it's",
    "let's": "let's",
    "lets": "let's",
}

# High-priority conversational seeds to guarantee instant everyday mobile readiness
CONVERSATIONAL_SEEDS = [
    ("how", ["are", "is", "about", "do", "can", "was"]),
    ("are", ["you", "we", "they", "there", "all"]),
    ("what", ["are", "is", "about", "do", "did", "happened", "time"]),
    ("where", ["are", "is", "do", "did", "were", "can"]),
    ("when", ["are", "will", "can", "is", "do", "did"]),
    ("why", ["are", "is", "not", "did", "do", "would"]),
    ("who", ["is", "are", "was", "will", "did"]),
    ("thank", ["you", "god", "heavens"]),
    ("thanks", ["for", "a", "again", "so", "to"]),
    ("you", ["are", "can", "will", "have", "know", "welcome", "too"]),
    ("i", ["am", "will", "have", "can", "know", "think", "love", "want", "need"]),
    ("i'm", ["good", "fine", "sorry", "here", "ready", "going", "doing", "glad"]),
    ("don't", ["know", "worry", "think", "have", "want", "like", "forget"]),
    ("can't", ["wait", "believe", "find", "do", "see", "hear", "complain"]),
    ("it's", ["a", "all", "been", "time", "okay", "good", "great", "hard"]),
    ("let", ["me", "us", "them", "him", "her"]),
    ("see", ["you", "it", "if", "what", "how"]),
    ("please", ["let", "help", "find", "send", "call", "check"]),
    ("sounds", ["good", "great", "like", "awesome", "fun"]),
    ("looking", ["forward", "for", "at", "good"]),
    ("take", ["care", "a", "your", "time", "it"]),
    ("have", ["a", "been", "to", "fun", "no"]),
    ("nice", ["to", "meeting", "day", "one"]),
    ("sorry", ["for", "about", "to", "i'm"]),
    ("happy", ["birthday", "new", "anniversary", "to"]),
    ("no", ["problem", "worries", "one", "way", "matter"]),
    ("will", ["be", "have", "do", "call", "see"]),
    ("call", ["me", "you", "back", "when", "later"]),
    ("tell", ["me", "them", "him", "her", "us"]),
    ("give", ["me", "up", "a", "them"]),
    ("text", ["me", "back", "you", "later"]),
    ("send", ["me", "the", "it", "you"]),
    ("at", ["home", "work", "school", "the", "least"]),
    ("on", ["my", "the", "your", "time", "it"]),
    ("in", ["the", "a", "my", "your", "our"]),
    ("to", ["be", "the", "do", "have", "see", "get"]),
    ("we", ["are", "will", "can", "have", "should", "need"]),
    ("they", ["are", "will", "were", "have", "can"]),
    ("he", ["is", "was", "will", "has", "said"]),
    ("she", ["is", "was", "will", "has", "said"]),
    ("love", ["you", "it", "this", "to"]),
    ("miss", ["you", "the", "it"]),
    ("welcome", ["to", "back", "home"]),
    ("good", ["morning", "night", "luck", "job", "idea", "afternoon", "evening"]),
    ("great", ["job", "idea", "work", "news", "time"]),
    ("best", ["regards", "wishes", "of", "way", "to"]),
    ("all", ["the", "good", "right", "set", "day"]),
    ("not", ["sure", "yet", "at", "only", "too"]),
    ("just", ["wanted", "checking", "got", "let", "called"]),
    ("can", ["you", "we", "i", "be", "do"]),
    ("could", ["you", "be", "have", "not"]),
    ("would", ["you", "be", "like", "have"]),
    ("should", ["be", "have", "we", "i"]),
    ("need", ["to", "help", "some", "more", "a"]),
    ("want", ["to", "you", "a", "some"]),
    ("like", ["to", "that", "this", "it", "you"]),
    ("know", ["what", "how", "that", "if", "about"]),
    ("think", ["about", "so", "that", "it's", "you"]),
    ("feel", ["free", "like", "good", "better"]),
    ("talk", ["to", "about", "later", "soon"]),
    ("keep", ["in", "it", "up", "going"]),
    ("make", ["sure", "sense", "it", "a"]),
    ("get", ["back", "it", "ready", "out", "to"]),
    ("go", ["to", "home", "out", "back"]),
    ("come", ["on", "to", "over", "back", "in"]),
    ("back", ["to", "home", "soon", "later"]),
    ("right", ["now", "here", "there", "away"]),
    ("as", ["well", "soon", "possible", "if", "much"]),
    ("so", ["much", "many", "good", "far", "that"]),
    ("too", ["much", "many", "late", "bad"]),
    ("very", ["good", "much", "well", "nice", "happy"]),
]

def clean_token(token: str) -> str:
    """Normalize and clean a single English token."""
    t = token.strip().lower()
    # Normalize curly apostrophes
    t = t.replace("’", "'").replace("`", "'")
    # Strip leading/trailing non-alphanumeric
    t = re.sub(r"^[^a-z]+|[^a-z]+$", "", t)
    if not t:
        return ""
    if t in CONTRACTION_MAP:
        t = CONTRACTION_MAP[t]
    if WORD_REGEX.match(t) and 1 <= len(t) <= 25:
        return t
    return ""

def process_sentence(sentence: str, bigram_counts: dict, unigram_counts: Counter, weight: int = 1):
    """Tokenize a sentence and accumulate bigram transition counts."""
    # Split on commas and symbols inside sentence
    words = []
    for raw in sentence.split():
        cleaned = clean_token(raw)
        if cleaned:
            words.append(cleaned)
    if len(words) < 2:
        return

    for i in range(len(words) - 1):
        w1 = words[i]
        w2 = words[i + 1]
        bigram_counts[w1][w2] += weight
        unigram_counts[w1] += weight

def ingest_count_2w(file_path: Path, bigram_counts: dict, unigram_counts: Counter):
    """Ingest Web 1T 2-word frequencies from Peter Norvig's count_2w.txt."""
    print(f"[*] Ingesting Web 1T bigrams from {file_path.name}...")
    valid_pairs = 0
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) != 2:
                continue
            pair = parts[0].split()
            if len(pair) != 2:
                continue
            w1 = clean_token(pair[0])
            w2 = clean_token(pair[1])
            if not w1 or not w2 or w1 == w2:
                continue
            try:
                raw_count = int(parts[1])
            except ValueError:
                continue

            # Scale large web counts using log-scaling to blend gracefully with conversational corpus
            scaled_count = int(math.log10(max(10, raw_count)) * 20)
            bigram_counts[w1][w2] += scaled_count
            unigram_counts[w1] += scaled_count
            valid_pairs += 1

    print(f"[+] Loaded {valid_pairs:,} valid bigram transitions from Web 1T.")

def ingest_alpaca_sentences(file_path: Path, bigram_counts: dict, unigram_counts: Counter):
    """Ingest conversational text from Stanford Alpaca dataset."""
    print(f"[*] Ingesting conversational sentences from {file_path.name}...")
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[-] Error loading Alpaca JSON: {e}")
        return

    sentence_count = 0
    for item in data:
        for key in ["instruction", "input", "output"]:
            text = item.get(key, "")
            if not text or not isinstance(text, str):
                continue
            sentences = SENTENCE_SPLIT_REGEX.split(text)
            for s in sentences:
                s_strip = s.strip()
                if len(s_strip) > 3:
                    # Higher weight for natural full sentences
                    process_sentence(s_strip, bigram_counts, unigram_counts, weight=5)
                    sentence_count += 1

    print(f"[+] Processed {sentence_count:,} sentence clauses from Alpaca dataset.")

def inject_conversational_seeds(bigram_counts: dict, unigram_counts: Counter):
    """Inject hand-tuned high-priority seeds for instantaneous chat readiness."""
    print("[*] Injecting mobile conversational seeds...")
    for w1, succs in CONVERSATIONAL_SEEDS:
        w1_norm = clean_token(w1)
        if not w1_norm:
            continue
        for rank, w2 in enumerate(succs):
            w2_norm = clean_token(w2)
            if not w2_norm or w1_norm == w2_norm:
                continue
            boost = 5000 - (rank * 300)
            bigram_counts[w1_norm][w2_norm] += boost
            unigram_counts[w1_norm] += boost

def build_english_bigrams():
    print("=" * 60)
    print("  English Bi-Gram Next-Word Extractor & Binary Compiler")
    print("=" * 60)

    bigram_counts = defaultdict(Counter)
    unigram_counts = Counter()

    count_file = RAW_ENGLISH_DIR / "count_2w.txt"
    if count_file.exists():
        ingest_count_2w(count_file, bigram_counts, unigram_counts)
    else:
        print(f"[!] Warning: {count_file.name} not found. Run download_en_corpora.py first.")

    alpaca_file = RAW_ENGLISH_DIR / "alpaca_data.json"
    if alpaca_file.exists():
        ingest_alpaca_sentences(alpaca_file, bigram_counts, unigram_counts)
    else:
        print(f"[!] Warning: {alpaca_file.name} not found.")

    inject_conversational_seeds(bigram_counts, unigram_counts)

    print(f"[+] Total distinct antecedent words: {len(bigram_counts):,}")

    # Prune and rank top 5 successors per antecedent
    print("[*] Pruning and ranking top 5 next-word predictions per entry...")
    final_bigrams = {}

    for w1, succ_map in bigram_counts.items():
        if len(w1) < 1:
            continue
        # Minimum total occurrences to retain (unless conversational seed)
        total_occurrences = unigram_counts[w1]
        if total_occurrences < 10 and len(succ_map) < 2:
            continue

        # Exclude self-loop transitions (e.g., 'the' -> 'the')
        top_succs = []
        for w2, _ in succ_map.most_common(12):
            if w2 != w1 and w2 not in top_succs:
                top_succs.append(w2)
            if len(top_succs) >= 5:
                break

        if top_succs:
            final_bigrams[w1] = top_succs

    print(f"[+] Final curated antecedent vocabulary: {len(final_bigrams):,}")

    # Write human-readable text file
    print(f"[*] Writing human-readable text file to {OUTPUT_TXT}...")
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write("# English Bi-gram Next-Word Dataset (Antecedent -> Predicted Next Words)\n")
        for w1 in sorted(final_bigrams.keys()):
            succs_str = ",".join(final_bigrams[w1])
            f.write(f"{w1}\t{succs_str}\n")
    print(f"[+] Saved {OUTPUT_TXT} ({OUTPUT_TXT.stat().st_size:,} bytes)")

    # Compile into binary index
    print(f"[*] Compiling compact binary index to {OUTPUT_BIN}...")
    compile_binary(final_bigrams, OUTPUT_BIN)

def compile_binary(bigrams_dict: dict, bin_path: Path):
    """
    Binary Layout for en_bigrams.bin:
    
    Header (24 bytes):
      [0..3]   Magic: b'BGBN' (or b'BGEN' - both supported by reader)
      [4..5]   Version: uint16 (1)
      [6..7]   Reserved: uint16 (0)
      [8..11]  Total Entries Count: uint32 (N)
      [12..15] Index Table Offset: uint32
      [16..19] Succ Array Offset: uint32
      [20..23] String Pool Offset: uint32
      
    Index Table (N * 12 bytes, sorted strictly by w1 UTF-8 byte order for binary search):
      [0..3]   w1_offset (uint32 offset in String Pool)
      [4..7]   succ_list_offset (uint32 offset in Successors Array)
      [8..9]   succ_count (uint16 count of predicted next words)
      [10..11] reserved (uint16)
      
    Successor Offset Array (Total Successors * 4 bytes):
      Array of uint32 offsets in String Pool for each successor word
      
    String Pool:
      Concatenated UTF-8 null-terminated strings: word1\0word2\0...
    """
    string_pool = bytearray()
    string_offset_map = {}

    def get_string_offset(word: str) -> int:
        if word not in string_offset_map:
            offset = len(string_pool)
            encoded = word.encode("utf-8") + b"\x00"
            string_pool.extend(encoded)
            string_offset_map[word] = offset
        return string_offset_map[word]

    # Sort antecedents strictly by UTF-8 byte order (for Android binary search)
    sorted_antecedents = sorted(bigrams_dict.keys(), key=lambda w: w.encode("utf-8"))

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

    # Calculate offsets
    header_size = 24
    index_table_offset = header_size
    index_table_size = len(index_entries) * 12
    succ_array_offset = index_table_offset + index_table_size
    succ_array_size = len(succ_array) * 4
    string_pool_offset = succ_array_offset + succ_array_size

    # Pack binary buffer
    out_buf = bytearray()
    # Header
    out_buf.extend(b"BGBN")                                    # 0..3 Magic (BGBN for universal compatibility)
    out_buf.extend(struct.pack("<H", 1))                       # 4..5 Version 1
    out_buf.extend(struct.pack("<H", 0))                       # 6..7 Reserved
    out_buf.extend(struct.pack("<I", len(index_entries)))       # 8..11 Total entries
    out_buf.extend(struct.pack("<I", index_table_offset))       # 12..15 Index Table Offset
    out_buf.extend(struct.pack("<I", succ_array_offset))       # 16..19 Succ Array Offset
    out_buf.extend(struct.pack("<I", string_pool_offset))      # 20..23 String Pool Offset

    # Index Table
    for w1_off, succ_off, count in index_entries:
        out_buf.extend(struct.pack("<IIHH", w1_off, succ_off, count, 0))

    # Successor Array
    for succ_w_off in succ_array:
        out_buf.extend(struct.pack("<I", succ_w_off))

    # String Pool
    out_buf.extend(string_pool)

    # Write file
    with open(bin_path, "wb") as f:
        f.write(out_buf)

    print(f"[+] Successfully compiled {bin_path.name}:")
    print(f"    - Total Antecedents (Index Table): {len(index_entries):,}")
    print(f"    - Total Successor Pointers: {len(succ_array):,}")
    print(f"    - Unique Strings in Pool: {len(string_offset_map):,}")
    print(f"    - Total Binary File Size: {len(out_buf):,} bytes ({len(out_buf)/1024/1024:.2f} MB)")

if __name__ == "__main__":
    build_english_bigrams()
