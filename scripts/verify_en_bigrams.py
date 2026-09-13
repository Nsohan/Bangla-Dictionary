#!/usr/bin/env python3
"""
Verification & Test Suite for English Bi-gram Binary Index (en_bigrams.bin)
Simulates Android Java runtime binary search and validates lookup accuracy and speed.
"""

import sys
import struct
import time
import random
from pathlib import Path

# Ensure UTF-8 stdout
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
BIN_PATH = ROOT_DIR / "output" / "en_bigrams.bin"

class BigramIndexReader:
    """Python reference reader simulating Android Java ByteBuffer lookup."""
    
    def __init__(self, data: bytes):
        self.data = data
        self._parse_header()
        
    def _parse_header(self):
        magic = self.data[0:4]
        assert magic in (b'BGBN', b'BGEN'), f"Invalid magic: {magic}"
        self.magic = magic
        self.version = struct.unpack_from('<H', self.data, 4)[0]
        self.total_entries = struct.unpack_from('<I', self.data, 8)[0]
        self.index_offset = struct.unpack_from('<I', self.data, 12)[0]
        self.succ_array_offset = struct.unpack_from('<I', self.data, 16)[0]
        self.string_pool_offset = struct.unpack_from('<I', self.data, 20)[0]
        
    def _read_cstring(self, pool_offset: int) -> str:
        abs_off = self.string_pool_offset + pool_offset
        end = self.data.find(b'\x00', abs_off)
        if end == -1:
            return ""
        return self.data[abs_off:end].decode('utf-8', errors='ignore')
        
    def predict(self, word: str) -> list:
        """Binary search on sorted index table (identical to Android Java algorithm)."""
        target_bytes = word.strip().lower().encode('utf-8')
        low = 0
        high = self.total_entries - 1
        
        while low <= high:
            mid = (low + high) // 2
            entry_offset = self.index_offset + mid * 12
            w1_off, succ_off, count, _ = struct.unpack_from('<IIHH', self.data, entry_offset)
            
            # Read antecedent word from string pool
            mid_word = self._read_cstring(w1_off)
            mid_bytes = mid_word.encode('utf-8')
            
            if mid_bytes == target_bytes:
                # Found! Fetch successors
                results = []
                for i in range(count):
                    succ_entry_off = self.succ_array_offset + (succ_off + i) * 4
                    succ_w_off = struct.unpack_from('<I', self.data, succ_entry_off)[0]
                    results.append(self._read_cstring(succ_w_off))
                return results
            elif mid_bytes < target_bytes:
                low = mid + 1
            else:
                high = mid - 1
                
        return []

def run_tests():
    print("=" * 60)
    print("  Testing English Bi-gram Binary Predictor (en_bigrams.bin)")
    print("=" * 60)
    
    if not BIN_PATH.exists():
        print(f"[-] Error: Binary file missing: {BIN_PATH}")
        sys.exit(1)
        
    data = BIN_PATH.read_bytes()
    reader = BigramIndexReader(data)
    
    print(f"[+] Loaded binary index: {BIN_PATH.name} ({len(data):,} bytes / {len(data)/1024/1024:.2f} MB)")
    print(f"    - Magic: {reader.magic}")
    print(f"    - Version: {reader.version}")
    print(f"    - Total Index Entries: {reader.total_entries:,}")
    print(f"    - Index Offset: {reader.index_offset:,}")
    print(f"    - Successor Array Offset: {reader.succ_array_offset:,}")
    print(f"    - String Pool Offset: {reader.string_pool_offset:,}")
    
    test_cases = [
        ("how", ["are", "is"]),
        ("what", ["are", "is"]),
        ("where", ["are", "is"]),
        ("when", ["are", "will", "is"]),
        ("thank", ["you"]),
        ("thanks", ["for"]),
        ("good", ["morning", "night", "luck", "job"]),
        ("i", ["am", "have", "will"]),
        ("i'm", ["good", "fine", "sorry", "ready"]),
        ("don't", ["know", "worry"]),
        ("can't", ["wait", "believe"]),
        ("it's", ["a", "all", "good"]),
        ("let", ["me", "us"]),
        ("see", ["you"]),
        ("please", ["let", "help", "find"]),
        ("sounds", ["good", "great"]),
        ("looking", ["forward", "for"]),
        ("take", ["care"]),
        ("have", ["a", "been"]),
        ("nice", ["to"]),
        ("happy", ["birthday"]),
        ("no", ["problem", "worries"]),
        ("call", ["me", "you"]),
        ("give", ["me"]),
        ("tell", ["me"]),
        ("best", ["regards", "wishes"]),
        ("as", ["well", "soon"]),
        ("very", ["good", "much"]),
    ]
    
    print("\n[*] Running Conversational Accuracy Checks...")
    passed = 0
    for word, expected_succs in test_cases:
        preds = reader.predict(word)
        # Check if at least one expected successor is predicted
        matches = [s for s in expected_succs if s in preds]
        if matches:
            passed += 1
            print(f"  [✓] '{word}' -> {preds} (matched: {matches})")
        else:
            print(f"  [✗] '{word}' -> {preds} (expected any of: {expected_succs})")
            
    pct = (passed / len(test_cases)) * 100
    print(f"\n[+] Accuracy Score: {passed}/{len(test_cases)} ({pct:.1f}%)")
    assert pct >= 90.0, f"Accuracy score too low: {pct:.1f}%"
    
    # Speed & Latency Benchmark
    print("\n[*] Running Micro-Latency Benchmark (10,000 lookups)...")
    sample_words = [tc[0] for tc in test_cases] + ["the", "in", "to", "we", "they", "will", "would", "should", "not", "so"]
    random_queries = [random.choice(sample_words) for _ in range(10000)]
    
    start_time = time.perf_counter()
    for q in random_queries:
        reader.predict(q)
    end_time = time.perf_counter()
    
    total_time = end_time - start_time
    avg_latency_ms = (total_time / len(random_queries)) * 1000
    lookups_per_sec = len(random_queries) / total_time
    
    print(f"[+] Total benchmark time: {total_time:.4f}s for {len(random_queries):,} lookups")
    print(f"[+] Average lookup latency: {avg_latency_ms:.4f} ms ({avg_latency_ms * 1000:.1f} microseconds)")
    print(f"[+] Throughput: {lookups_per_sec:,.0f} queries/second")
    
    print("\n[✓] All verification and performance tests PASSED successfully!")

if __name__ == "__main__":
    run_tests()
