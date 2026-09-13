#!/usr/bin/env python3
"""
Utility script to import and merge raw wordlists into AOSP .combined format.
Usage:
    python wordlist_merger.py input_words.txt output_combined.txt --default-freq 200
"""

import sys
import argparse
from pathlib import Path

def convert_wordlist(input_path, output_path, default_freq=200):
    words = {}
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            word = parts[0]
            freq = default_freq
            if len(parts) > 1:
                try:
                    if parts[1].startswith("f="):
                        freq = int(parts[1][2:])
                    else:
                        freq = int(parts[1])
                except ValueError:
                    freq = default_freq
            words[word] = max(words.get(word, 0), min(max(freq, 1), 255))

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"dictionary=main:bn,description=Imported Wordlist,locale=bn,date=1700000000,version=1\n")
        for word, freq in sorted(words.items(), key=lambda x: -x[1]):
            f.write(f"word={word},f={freq}\n")

    print(f"[+] Converted {len(words)} unique words to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert raw text wordlist to AOSP .combined format")
    parser.add_argument("input", help="Input raw text file (one word per line or 'word freq')")
    parser.add_argument("output", help="Output .combined file")
    parser.add_argument("--default-freq", type=int, default=200, help="Default frequency (1-255)")
    args = parser.parse_args()

    convert_wordlist(args.input, args.output, args.default_freq)
