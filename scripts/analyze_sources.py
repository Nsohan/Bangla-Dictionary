import re
import unicodedata
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

bengali_char_pattern = re.compile(r'^[\u0980-\u09FF\u200c\u200d]+$')
# Dependent vowel signs and diacritics that cannot start a word
invalid_start = set('\u09be\u09bf\u09c0\u09c1\u09c2\u09c3\u09c4\u09c7\u09c8\u09cb\u09cc\u09cd\u0981\u0982\u0983\u09bc')

def is_valid_bangla_word(w: str) -> bool:
    w = unicodedata.normalize('NFC', w.strip())
    if not w or len(w) < 1:
        return False
    if w[0] in invalid_start:
        return False
    if not bengali_char_pattern.match(w):
        return False
    # Avoid tokens composed purely of digits
    if all('\u09e6' <= c <= '\u09ef' for c in w):
        return False
    # Avoid standalone single diacritics
    if len(w) == 1 and w in invalid_start:
        return False
    return True

sources = {
    'bangla_words.combined': 'sources/bangla_words.combined',
    'Bangla_root_word.txt': 'raw_data_sources/Bangla_root_word.txt',
    'BengaliDictionary_93..csv': 'raw_data_sources/BengaliDictionary_93..csv',
    'BengaliWordList_40.txt': 'raw_data_sources/BengaliWordList_40.txt',
    'BengaliWordList_48.txt': 'raw_data_sources/BengaliWordList_48.txt',
    'BengaliWordList_112.txt': 'raw_data_sources/BengaliWordList_112.txt',
    'BengaliWordList_439.txt': 'raw_data_sources/BengaliWordList_439.txt',
    'bangla_number.txt': 'raw_data_sources/bangla_number.txt'
}

all_valid = {}
source_counts = {}

for name, p in sources.items():
    path = Path(p)
    if not path.exists():
        continue
    valid_count = 0
    total_lines = 0
    with open(path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            total_lines += 1
            candidates = []
            if name.endswith('.csv'):
                parts = line.split(';')
                if len(parts) >= 3:
                    raw_text = parts[2].replace('/', ' ').replace(',', ' ').replace('(', ' ').replace(')', ' ')
                    candidates = raw_text.split()
            elif name.endswith('.combined'):
                if line.startswith('word='):
                    candidates = [line.split(',')[0][len('word='):]]
            else:
                candidates = line.split()

            for c in candidates:
                c = c.strip(' \t\r\n.,;:!?"\'()[]{}<>-–—')
                if is_valid_bangla_word(c):
                    word = unicodedata.normalize('NFC', c)
                    valid_count += 1
                    if word not in all_valid:
                        all_valid[word] = set()
                    all_valid[word].add(name)
    source_counts[name] = (total_lines, valid_count)
    print(f"{name:<32}: read {total_lines:>7} lines -> {valid_count:>7} valid words extracted")

print("-" * 60)
print(f"Total UNIQUE valid Bangla words across all sources: {len(all_valid)}")

# Distribution of word occurrences across sources
freq_in_sources = {}
for w, srcs in all_valid.items():
    cnt = len(srcs)
    freq_in_sources[cnt] = freq_in_sources.get(cnt, 0) + 1

print("\nOccurrence across distinct sources:")
for cnt in sorted(freq_in_sources.keys()):
    print(f"  Appears in {cnt} source(s): {freq_in_sources[cnt]:>6} words")
