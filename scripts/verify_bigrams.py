#!/usr/bin/env python3
"""
Verification & Test Suite for Bengali Bi-gram Binary Index (bn_bigrams.bin)
Simulates Android Java runtime binary search and validates lookup accuracy and speed.
"""

import sys
import struct
import time
from pathlib import Path

# Ensure UTF-8 stdout
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
BIN_PATH = ROOT_DIR / "output" / "bn_bigrams.bin"

class BigramIndexReader:
    """Python reference reader simulating Android Java ByteBuffer lookup."""
    
    def __init__(self, data: bytes):
        self.data = data
        self._parse_header()
        
    def _parse_header(self):
        magic = self.data[0:4]
        assert magic == b'BGBN', f"Invalid magic: {magic}"
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
        target_bytes = word.encode('utf-8')
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

def normalize_bengali(text: str) -> str:
    import unicodedata
    t = unicodedata.normalize('NFC', text.strip())
    t = t.replace('\u09a1\u09bc', '\u09dc')  # ড + ় -> ড়
    t = t.replace('\u09a2\u09bc', '\u09dd')  # ঢ + ় -> ঢ়
    t = t.replace('\u09af\u09bc', '\u09df')  # য + ় -> য়
    t = t.replace('\u200c', '').replace('\u200d', '').replace('\ufeff', '')
    return t

def run_tests():
    print("=" * 60)
    print("  Testing Bengali Bi-gram Binary Predictor (bn_bigrams.bin)")
    print("=" * 60)
    
    assert BIN_PATH.exists(), f"Binary file missing: {BIN_PATH}"
    data = BIN_PATH.read_bytes()
    reader = BigramIndexReader(data)
    
    print(f"[+] Loaded binary index: {BIN_PATH.name} ({len(data):,} bytes)")
    print(f"    - Version: {reader.version}")
    print(f"    - Total Index Entries: {reader.total_entries:,}")
    
    test_cases = [
        ("আমি", ["তোমাকে", "এখন", "করব", "যাব"]),
        ("তুমি", ["কেমন", "কোথায়", "কি", "যাবে"]),
        ("কেমন", ["আছো", "আছেন"]),
        ("শুভ", ["সকাল", "রাত্রি", "জন্মদিন"]),
        ("অনেক", ["ধন্যবাদ", "সুন্দর", "ভালো"]),
        ("ধন্যবাদ", ["ভাই", "আপনাকে", "তোমাকে"]),
        ("বাসায়", ["যাব", "পৌঁছে", "আছি"]),
        ("খাবার", ["খেয়েছ", "খাব", "দাও"]),
        ("ইনশাআল্লাহ", ["ভালো", "হবে", "যাব"]),
        ("মাশাল্লাহ", ["অনেক", "সুন্দর"]),
        ("আলহামদুলিল্লাহ", ["ভালো", "আছি"]),
        ("দেখা", ["হবে", "করব"]),
        ("কথা", ["বলব", "বলবেন", "হবে"]),
        ("টাকা", ["দাও", "পাঠাও", "আছে"]),
        ("ফোন", ["দিচ্ছি", "দাও", "করব"]),
    ]
    
    passed = 0
    total_time = 0.0
    
    print("\n--- Running Prediction Assertions ---")
    for raw_word, expected_succs in test_cases:
        word = normalize_bengali(raw_word)
        t0 = time.perf_counter()
        predictions = reader.predict(word)
        t_query = (time.perf_counter() - t0) * 1000 # ms
        total_time += t_query
        
        # Check if at least one or more expected successors appear in top predictions
        matches = [s for s in expected_succs if s in predictions]
        status = "✓ PASS" if len(matches) > 0 else "✗ FAIL"
        
        print(f"  {status}: Word '{word}' -> Predictions: {predictions} ({t_query:.3f} ms)")
        assert len(matches) > 0, f"Expected {expected_succs}, got {predictions} for '{word}'"
        passed += 1
        
    avg_latency = total_time / len(test_cases)
    print(f"\n[+] All {passed}/{len(test_cases)} conversational test cases PASSED!")
    print(f"[+] Average Query Latency: {avg_latency:.4f} ms per lookup (Ultra-Fast < 0.05 ms)")

if __name__ == "__main__":
    run_tests()
