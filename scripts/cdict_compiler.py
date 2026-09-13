#!/usr/bin/env python3
"""
Pure Python Cdict Dictionary Compiler
Compatible with libcdict format version 1 (used by OsthirKeyboard / AnySoftKeyboard cdict engine).
Replaces the OCaml/dune cdict-tool dependency.
"""

import sys
import struct
import math
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Any

FORMAT_VERSION = 1
FORMAT_4_BITS = 1
FORMAT_8_BITS = 2
FORMAT_16_BITS = 4
FORMAT_24_BITS = 6

BRANCHES_TAG = 0
PREFIX_TAG = 1

PTR_FLAG_FINAL = 1
PTR_OFFSET_MASK = ~1

def width_of_last_full_level(length: int) -> Tuple[int, int]:
    s = 1
    while True:
        s_prime = (s * 2) + 1
        if s_prime > length:
            return ((s // 2) + 1, length - s)
        s = s_prime

def pivot(length: int) -> int:
    width, last_level = width_of_last_full_level(length)
    if last_level <= width:
        return (length + last_level) // 2
    else:
        return (width * 2) - 1

def complete_tree_of_sorted_list(src: list) -> list:
    length = len(src)
    if length == 0:
        return []
    dst = [None] * length
    def loop(lo: int, hi: int, dsti: int):
        if lo > hi:
            return
        mid = lo + pivot(hi - lo + 1)
        dst[dsti] = src[mid]
        loop(lo, mid - 1, (dsti * 2) + 1)
        loop(mid + 1, hi, (dsti * 2) + 2)
    loop(0, length - 1, 0)
    return dst

def k_medians(data: List[int], k: int = 16) -> List[int]:
    length = len(data)
    if length == 0:
        return []
    indexes = sorted(range(length), key=lambda i: data[i])
    res = [0] * length
    cluster_size = max(1, length // k)
    
    prev_val = data[indexes[0]]
    prev_cluster = 0
    res[indexes[0]] = 0
    
    for i in range(1, length):
        idx = indexes[i]
        val = data[idx]
        cluster = min(k - 1, i // cluster_size)
        if val == prev_val:
            cluster = prev_cluster
        res[idx] = cluster
        prev_cluster = cluster
        prev_val = val
    return res

def encode_freq_array(freqs: List[int]) -> bytes:
    compressed = k_medians(freqs, 16)
    length = len(compressed)
    buf = bytearray((length + 1) // 2)
    for i, f in enumerate(compressed):
        f = f & 0xF
        byte_idx = i // 2
        if i % 2 == 0:
            buf[byte_idx] = f
        else:
            buf[byte_idx] = (f << 4) | buf[byte_idx]
    return bytes(buf)

def detect_format(arr: List[int], signed: Optional[bool] = None) -> int:
    if not arr:
        return FORMAT_8_BITS
    min_val = min(arr)
    max_val = max(arr)
    if signed is None:
        signed = min_val < 0
    
    if signed:
        min_abs = (-min_val - 1) if min_val < 0 else min_val
        max_abs = max(min_abs, max_val)
        if max_abs <= 0x7:
            return FORMAT_4_BITS
        elif max_abs <= 0x7F:
            return FORMAT_8_BITS
        elif max_abs <= 0x7FFF:
            return FORMAT_16_BITS
        else:
            return FORMAT_24_BITS
    else:
        max_abs = max_val
        if max_abs <= 0xF:
            return FORMAT_4_BITS
        elif max_abs <= 0xFF:
            return FORMAT_8_BITS
        elif max_abs <= 0xFFFF:
            return FORMAT_16_BITS
        else:
            return FORMAT_24_BITS

def pack_sized_int_array(arr: List[int], fmt: int) -> bytes:
    n = len(arr)
    if fmt == FORMAT_4_BITS:
        buf = bytearray((n + 1) // 2)
        for i, val in enumerate(arr):
            v = val & 0xF
            idx = i >> 1
            if i & 1:
                buf[idx] = (v << 4) | (buf[idx] & 0xF)
            else:
                buf[idx] = v | (buf[idx] & 0xF0)
        return bytes(buf)
    elif fmt == FORMAT_8_BITS:
        return bytes(val & 0xFF for val in arr)
    elif fmt == FORMAT_16_BITS:
        out = bytearray(n * 2)
        for i, val in enumerate(arr):
            out[i*2 : i*2+2] = (val & 0xFFFF).to_bytes(2, "big", signed=False)
        return bytes(out)
    elif fmt == FORMAT_24_BITS:
        out = bytearray(n * 3)
        for i, val in enumerate(arr):
            v = val & 0xFFFFFF
            out[i*3] = (v >> 16) & 0xFF
            out[i*3 + 1] = (v >> 8) & 0xFF
            out[i*3 + 2] = v & 0xFF
        return bytes(out)
    raise ValueError(f"Unknown format: {fmt}")

class DFATransition:
    def __init__(self, c: int, next_id: int, number: int = -1, final: bool = False):
        self.c = c # uint8 byte
        self.next_id = next_id
        self.number = number
        self.final = final

class MinimalDFA:
    def __init__(self):
        self.states = {0: []} # id -> list of DFATransition
        self._next_id = 1
        self.register = {} # state_tuple -> id

    def fresh_id(self) -> int:
        nid = self._next_id
        self._next_id += 1
        return nid

    def common_prefix(self, word: bytes) -> Tuple[int, int, List[DFATransition]]:
        curr_id = 0
        for i, b in enumerate(word):
            st = self.states[curr_id]
            match = next((tr for tr in st if tr.c == b), None)
            if match:
                curr_id = match.next_id
            else:
                return (i, curr_id, st)
        return (len(word), curr_id, self.states[curr_id])

    def add_suffix(self, sti: int, st: List[DFATransition], suffix: bytes):
        length = len(suffix)
        if length == 0:
            return
        
        # Build chain from end to beginning
        curr_id = self.fresh_id()
        self.states[curr_id] = []
        final = True
        
        for i in reversed(range(length)):
            b = suffix[i]
            tr = DFATransition(c=b, next_id=curr_id, number=-1, final=final)
            if i > 0:
                parent_id = self.fresh_id()
                self.states[parent_id] = [tr]
                curr_id = parent_id
                final = False
            else:
                st.append(tr)
                self.states[sti] = st

    def replace_or_register(self, sti: int, st: List[DFATransition]) -> Tuple[int, List[DFATransition]]:
        if not st:
            return sti, st
        last_tr = st[-1]
        child_id = last_tr.next_id
        child_st = self.states[child_id]
        
        new_child_id, new_child_st = self.replace_or_register(child_id, child_st)
        
        key = tuple((tr.c, tr.next_id, tr.final) for tr in new_child_st)
        if key in self.register:
            existing_id = self.register[key]
            last_tr.next_id = existing_id
            if existing_id != child_id and child_id in self.states:
                del self.states[child_id]
        else:
            self.register[key] = child_id
            
        return sti, st

    def add_word(self, word: bytes):
        prefix_len, last_sti, last_st = self.common_prefix(word)
        suffix = word[prefix_len:]
        self.replace_or_register(last_sti, last_st)
        self.add_suffix(last_sti, last_st, suffix)

    def compute_numbers(self):
        def map_st(sti: int) -> Tuple[int, int]:
            st = self.states[sti]
            cum_index = 0
            for tr in st:
                tr.number = cum_index
                child_size = map_st(tr.next_id)[1]
                size = (1 if tr.final else 0) + child_size
                cum_index += size
            return sti, cum_index
        map_st(0)

def build_dfa_from_words(words_bytes: List[bytes]) -> MinimalDFA:
    dfa = MinimalDFA()
    for w in words_bytes:
        dfa.add_word(w)
    dfa.replace_or_register(0, dfa.states[0])
    dfa.compute_numbers()
    return dfa

class PrefixNode:
    def __init__(self, prefix: bytes, next_id: int, final: bool):
        self.prefix = prefix
        self.next_id = next_id
        self.final = final

class BranchesNode:
    def __init__(self, labels: bytes, branches: List[Tuple[int, bool]], numbers: List[int]):
        self.labels = labels # Complete tree order
        self.branches = branches # (next_id, final) in complete tree order
        self.numbers = numbers # numbers in complete tree order

def optimize_dfa(dfa: MinimalDFA) -> Tuple[Dict[int, Any], int]:
    optimized = {}
    seen = {}
    
    def fold_prefix(prefix: bytearray, next_id: int, final: bool) -> Tuple[bytes, int, bool]:
        if final or len(prefix) >= 127:
            return bytes(prefix), next_id, final
        st = dfa.states.get(next_id, [])
        if len(st) == 1 and st[0].number == 0:
            tr = st[0]
            prefix.append(tr.c)
            return fold_prefix(prefix, tr.next_id, tr.final)
        return bytes(prefix), next_id, final

    def convert_state(sti: int) -> int:
        if sti in seen:
            return seen[sti]
        
        st = dfa.states.get(sti, [])
        if len(st) == 1 and st[0].number == 0:
            tr = st[0]
            prefix_bytes, next_id, final = fold_prefix(bytearray([tr.c]), tr.next_id, tr.final)
            opt_next_id = convert_state(next_id)
            node = PrefixNode(prefix_bytes, opt_next_id, final)
            node_id = sti
            optimized[node_id] = node
            seen[sti] = node_id
            return node_id
        else:
            sorted_branches = []
            for tr in st:
                opt_next_id = convert_state(tr.next_id)
                sorted_branches.append((tr.c, tr.number, opt_next_id, tr.final))
            
            sorted_branches.sort(key=lambda b: b[0])
            tree = complete_tree_of_sorted_list(sorted_branches)
            labels = bytes(item[0] for item in tree)
            branches = [(item[2], item[3]) for item in tree]
            numbers = [item[1] for item in tree]
            
            node = BranchesNode(labels, branches, numbers)
            node_id = sti
            optimized[node_id] = node
            seen[sti] = node_id
            return node_id

    root_id = convert_state(0)
    return optimized, root_id

class CDictSerializer:
    def __init__(self):
        self.buf = bytearray(1024 * 1024)
        self.end = 0

    def align2(self, offset: int) -> int:
        return (offset + 1) & ~1

    def alloc(self, n: int) -> int:
        off = self.align2(self.end)
        end = off + n
        self.end = end
        if end > len(self.buf):
            new_buf = bytearray(max(end * 2, len(self.buf) * 2))
            new_buf[:len(self.buf)] = self.buf
            self.buf = new_buf
        return off

    def serialize(self, dict_configs: List[dict]) -> bytes:
        dict_count = len(dict_configs)
        header_off = self.alloc(5 + 24 * dict_count)
        
        # Write magic, version, dict_count
        self.buf[header_off:header_off+3] = b"Dic"
        self.buf[header_off+3] = FORMAT_VERSION
        self.buf[header_off+4] = dict_count

        for i, cfg in enumerate(dict_configs):
            dheader_off = header_off + 5 + 24 * i
            self.write_dict(dheader_off, cfg)

        return bytes(self.buf[:self.end])

    def write_dict(self, dheader_off: int, cfg: dict):
        name = cfg["name"]
        nodes = cfg["nodes"]
        root_id = cfg["root_id"]
        freq_bytes = cfg["freq_bytes"]
        aliases = cfg["aliases"]

        seen = {}

        def write_node(next_id: int, final: bool) -> Tuple[int, int]:
            if next_id in seen:
                return seen[next_id], (1 if final else 0)
            
            node = nodes[next_id]
            if isinstance(node, PrefixNode):
                child_off, child_final = write_node(node.next_id, node.final)
                p_len = len(node.prefix)
                node_off = self.alloc(4 + p_len)
                
                rel_offset = child_off - node_off
                ptr_val = (rel_offset & PTR_OFFSET_MASK) | child_final
                
                header = (p_len << 1) | PREFIX_TAG
                self.buf[node_off] = header
                self.buf[node_off+1] = (ptr_val >> 16) & 0xFF
                self.buf[node_off+2] = (ptr_val >> 8) & 0xFF
                self.buf[node_off+3] = ptr_val & 0xFF
                self.buf[node_off+4 : node_off+4+p_len] = node.prefix
                
                seen[next_id] = node_off
                return node_off, (1 if final else 0)
            
            elif isinstance(node, BranchesNode):
                encoded_branches = []
                for child_id, child_final in node.branches:
                    c_off, c_fin = write_node(child_id, child_final)
                    encoded_branches.append((c_off, c_fin))

                node_off = self.alloc(0)
                
                branch_ptrs = [((c_off - node_off) & PTR_OFFSET_MASK) | c_fin for c_off, c_fin in encoded_branches]
                branches_fmt = detect_format(branch_ptrs, signed=True)
                numbers_fmt = detect_format(node.numbers, signed=False)

                packed_branches = pack_sized_int_array(branch_ptrs, branches_fmt)
                packed_numbers = pack_sized_int_array(node.numbers, numbers_fmt)

                length = len(node.labels)
                total_size = 2 + length + len(packed_branches) + len(packed_numbers)
                node_off_real = self.alloc(total_size)
                assert node_off == node_off_real

                header = (branches_fmt << 1) | (numbers_fmt << 4) | BRANCHES_TAG
                self.buf[node_off] = header
                self.buf[node_off+1] = length
                self.buf[node_off+2 : node_off+2+length] = node.labels
                
                br_start = node_off + 2 + length
                self.buf[br_start : br_start + len(packed_branches)] = packed_branches
                num_start = br_start + len(packed_branches)
                self.buf[num_start : num_start + len(packed_numbers)] = packed_numbers

                seen[next_id] = node_off
                return node_off, (1 if final else 0)

        root_off, root_final = write_node(root_id, False)
        root_ptr = (root_off & PTR_OFFSET_MASK) | root_final

        freq_off = self.alloc(len(freq_bytes))
        self.buf[freq_off : freq_off + len(freq_bytes)] = freq_bytes

        name_bytes = name.encode("utf-8") + b"\x00"
        name_off = self.alloc(len(name_bytes))
        self.buf[name_off : name_off + len(name_bytes)] = name_bytes

        # Write Aliases
        aliases_count = len(aliases)
        if aliases_count > 0:
            keys = [a[0] for a in aliases]
            vals = [a[1] for a in aliases]
            keys_fmt = detect_format(keys, signed=False)
            vals_fmt = detect_format(vals, signed=False)
            packed_keys = pack_sized_int_array(keys, keys_fmt)
            packed_vals = pack_sized_int_array(vals, vals_fmt)

            keys_off = self.alloc(len(packed_keys))
            self.buf[keys_off : keys_off + len(packed_keys)] = packed_keys
            vals_off = self.alloc(len(packed_vals))
            self.buf[vals_off : vals_off + len(packed_vals)] = packed_vals
            aliases_header = (keys_fmt & 7) | ((vals_fmt & 7) << 3)
        else:
            keys_fmt = FORMAT_8_BITS
            vals_fmt = FORMAT_8_BITS
            aliases_header = (keys_fmt & 7) | ((vals_fmt & 7) << 3)
            keys_off = self.alloc(0)
            vals_off = self.alloc(0)

        # Write dict header
        struct.pack_into(">iii", self.buf, dheader_off, name_off, root_ptr, freq_off)
        self.buf[dheader_off + 12] = aliases_header
        self.buf[dheader_off + 13] = (aliases_count >> 16) & 0xFF
        self.buf[dheader_off + 14] = (aliases_count >> 8) & 0xFF
        self.buf[dheader_off + 15] = aliases_count & 0xFF
        struct.pack_into(">ii", self.buf, dheader_off + 16, keys_off, vals_off)

def parse_aosp_combined(file_path: Path) -> List[Tuple[str, int, List[str]]]:
    """Parse .combined file. Returns [(word, freq, [shortcuts])]"""
    words = []
    curr_word = None
    curr_freq = 1
    curr_shortcuts = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("dictionary="):
                continue
            if line.startswith("word="):
                if curr_word is not None:
                    words.append((curr_word, curr_freq, curr_shortcuts))
                    curr_shortcuts = []
                parts = line.split(",")
                curr_word = parts[0][len("word="):]
                curr_freq = 1
                for p in parts[1:]:
                    if p.startswith("f="):
                        curr_freq = int(p[2:])
            elif line.startswith("shortcut="):
                parts = line.split(",")
                sc = parts[0][len("shortcut="):]
                curr_shortcuts.append(sc)
    if curr_word is not None:
        words.append((curr_word, curr_freq, curr_shortcuts))
    return words

def parse_plain_text(file_path: Path) -> List[Tuple[str, int, List[str]]]:
    counts = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            w = line.strip()
            if w:
                counts[w] = counts.get(w, 0) + 1
    return [(w, count, []) for w, count in counts.items()]

def build_dict_config(name: str, input_path: Path) -> dict:
    if input_path.suffix == ".combined":
        raw_words = parse_aosp_combined(input_path)
    else:
        raw_words = parse_plain_text(input_path)

    # Expand shortcuts
    all_entries = []
    for w, freq, shortcuts in raw_words:
        all_entries.append((w, freq, shortcuts))
        for sc in shortcuts:
            all_entries.append((sc, 1, []))

    # Deduplicate by word string, preserving first occurrence
    unique_map = {}
    for w, freq, shortcuts in all_entries:
        if w not in unique_map:
            unique_map[w] = (freq, shortcuts)

    # Sort lexicographically by UTF-8 bytes
    sorted_words = sorted(unique_map.keys(), key=lambda s: s.encode("utf-8"))
    word_to_idx = {w: i for i, w in enumerate(sorted_words)}

    # Frequencies
    freqs = [unique_map[w][0] for w in sorted_words]
    freq_bytes = encode_freq_array(freqs)

    # Build Aliases
    aliases_raw = []
    for i, w in enumerate(sorted_words):
        _, shortcuts = unique_map[w]
        if shortcuts:
            target = shortcuts[0]
            # resolve target recursively
            while target in unique_map and unique_map[target][1]:
                target = unique_map[target][1][0]
            if target in word_to_idx:
                target_idx = word_to_idx[target]
                aliases_raw.append((i, target_idx))

    # Sort aliases by key and arrange as complete tree
    aliases_raw.sort(key=lambda a: a[0])
    aliases_tree = complete_tree_of_sorted_list(aliases_raw)

    # Build Minimal DFA and optimize
    words_bytes = [w.encode("utf-8") for w in sorted_words]
    dfa = build_dfa_from_words(words_bytes)
    nodes, root_id = optimize_dfa(dfa)

    return {
        "name": name,
        "nodes": nodes,
        "root_id": root_id,
        "freq_bytes": freq_bytes,
        "aliases": aliases_tree,
        "word_count": len(sorted_words),
        "aliases_count": len(aliases_tree)
    }

def compile_dictionaries(inputs: List[Tuple[str, Path]], output_path: Path):
    dict_configs = []
    for name, path in inputs:
        print(f"[*] Processing {name}:{path}...")
        cfg = build_dict_config(name, path)
        print(f"    -> {cfg['word_count']} words, {cfg['aliases_count']} aliases")
        dict_configs.append(cfg)

    serializer = CDictSerializer()
    dict_bytes = serializer.serialize(dict_configs)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(dict_bytes)
    print(f"[+] Output written to {output_path} ({len(dict_bytes)} bytes)")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python cdict_compiler.py -o <output_file> [name:file ...]")
        sys.exit(1)
    
    output_file = None
    inputs = []
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "-o":
            i += 1
            output_file = Path(sys.argv[i])
        elif ":" in arg:
            name, path = arg.split(":", 1)
            inputs.append((name, Path(path)))
        i += 1

    if not output_file or not inputs:
        print("Error: Missing output file or input dictionaries")
        sys.exit(1)

    compile_dictionaries(inputs, output_file)
