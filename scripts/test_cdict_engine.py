import struct
from pathlib import Path

# Formats
FORMAT_4_BITS = 1
FORMAT_8_BITS = 2
FORMAT_16_BITS = 4
FORMAT_24_BITS = 6

PTR_FLAG_FINAL = 1
PTR_OFFSET_MASK = ~1

def sized_int_array_unsigned(buf, fmt, i):
    if fmt == FORMAT_8_BITS:
        return buf[i]
    if fmt == FORMAT_4_BITS:
        byte = buf[i >> 1]
        return (byte >> 4) if (i & 1) else (byte & 0xF)
    idx = (fmt * i) >> 1
    if fmt == FORMAT_16_BITS:
        return (buf[idx] << 8) | buf[idx + 1]
    if fmt == FORMAT_24_BITS:
        return (buf[idx] << 16) | (buf[idx + 1] << 8) | buf[idx + 2]
    raise ValueError(f"Unknown format {fmt}")

def sized_int_array_signed(buf, fmt, i):
    if fmt == FORMAT_8_BITS:
        v = buf[i]
        return v - 256 if v >= 128 else v
    if fmt == FORMAT_4_BITS:
        byte = buf[i >> 1]
        v = (byte >> 4) if (i & 1) else (byte & 0xF)
        return (v | ~0xF) if (v & 0x8) else v
    idx = (fmt * i) >> 1
    if fmt == FORMAT_16_BITS:
        v = (buf[idx] << 8) | buf[idx + 1]
        return v - 65536 if v >= 32768 else v
    if fmt == FORMAT_24_BITS:
        v = (buf[idx] << 16) | (buf[idx + 1] << 8) | buf[idx + 2]
        return v - 16777216 if v >= 8388608 else v
    raise ValueError(f"Unknown format {fmt}")

def format_array_size(fmt, n):
    return ((fmt * n) + 1) >> 1

class CDict:
    def __init__(self, data: bytes):
        self.data = data
        assert data[:3] == b"Dic"
        assert data[3] == 1 # version 1
        self.dict_count = data[4]
        self.dicts = {}
        
        offset = 5
        for i in range(self.dict_count):
            name_off, root_ptr, freq_off = struct.unpack(">iii", data[offset:offset+12])
            aliases_header = data[offset+12]
            aliases_len = int.from_bytes(data[offset+13:offset+16], "big")
            aliases_keys, aliases_values = struct.unpack(">ii", data[offset+16:offset+24])
            
            name_end = data.find(b"\x00", name_off)
            name = data[name_off:name_end].decode("utf-8")
            
            keys_fmt = aliases_header & 7
            vals_fmt = (aliases_header >> 3) & 7
            
            self.dicts[name] = {
                "name": name,
                "root_ptr": root_ptr,
                "freq_off": freq_off,
                "aliases_len": aliases_len,
                "keys_fmt": keys_fmt,
                "vals_fmt": vals_fmt,
                "aliases_keys": aliases_keys,
                "aliases_values": aliases_values,
            }
            offset += 24

    def resolve_alias(self, dname, index):
        d = self.dicts[dname]
        length = d["aliases_len"]
        if length == 0:
            return -1
        keys_buf = self.data[d["aliases_keys"]:]
        vals_buf = self.data[d["aliases_values"]:]
        keys_fmt = d["keys_fmt"]
        vals_fmt = d["vals_fmt"]
        
        i = 0
        while i < length:
            ar_i = sized_int_array_unsigned(keys_buf, keys_fmt, i)
            if ar_i == index:
                return sized_int_array_unsigned(vals_buf, vals_fmt, i)
            i = i * 2 + (1 if index < ar_i else 2)
        return -1

    def find_node(self, parent_offset, ptr, word_bytes, index):
        is_final = bool(ptr & PTR_FLAG_FINAL)
        offset = parent_offset + (ptr & PTR_OFFSET_MASK)
        
        if len(word_bytes) == 0:
            return is_final, index
            
        if is_final:
            index += 1
            
        node_kind = self.data[offset] & 1
        if node_kind == 0: # BRANCHES
            header = self.data[offset]
            length = self.data[offset + 1]
            branches_fmt = (header >> 1) & 7
            numbers_fmt = (header >> 4) & 7
            
            labels = self.data[offset + 2 : offset + 2 + length]
            branches_start = offset + 2 + length
            branches_buf = self.data[branches_start:]
            numbers_start = branches_start + format_array_size(branches_fmt, length)
            numbers_buf = self.data[numbers_start:]
            
            c = word_bytes[0]
            i = 0
            while i < length:
                l = labels[i]
                if c == l:
                    num = sized_int_array_unsigned(numbers_buf, numbers_fmt, i)
                    b_ptr = sized_int_array_signed(branches_buf, branches_fmt, i)
                    return self.find_node(offset, b_ptr, word_bytes[1:], index + num)
                elif c < l:
                    i = i * 2 + 1
                else:
                    i = i * 2 + 2
            return False, index
        else: # PREFIX
            header = self.data[offset]
            p_len = header >> 1
            raw_ptr = self.data[offset + 1 : offset + 4]
            next_ptr = int.from_bytes(raw_ptr, "big", signed=True)
            prefix = self.data[offset + 4 : offset + 4 + p_len]
            
            if word_bytes.startswith(prefix):
                return self.find_node(offset, next_ptr, word_bytes[len(prefix):], index)
            return False, index

    def get_word_at_index(self, dname, index):
        d = self.dicts[dname]
        return self._get_word_node(0, d["root_ptr"], index)

    def _get_word_node(self, parent_offset, ptr, index):
        is_final = bool(ptr & PTR_FLAG_FINAL)
        offset = parent_offset + (ptr & PTR_OFFSET_MASK)
        if is_final:
            if index == 0:
                return b""
            index -= 1
            
        node_kind = self.data[offset] & 1
        if node_kind == 0: # BRANCHES
            header = self.data[offset]
            length = self.data[offset + 1]
            branches_fmt = (header >> 1) & 7
            numbers_fmt = (header >> 4) & 7
            
            labels = self.data[offset + 2 : offset + 2 + length]
            branches_start = offset + 2 + length
            branches_buf = self.data[branches_start:]
            numbers_start = branches_start + format_array_size(branches_fmt, length)
            numbers_buf = self.data[numbers_start:]
            
            next_b = 0
            next_num = 0
            dst_char = None
            i = 0
            while i < length:
                ni = sized_int_array_unsigned(numbers_buf, numbers_fmt, i)
                bi = sized_int_array_signed(branches_buf, branches_fmt, i)
                if ni > index:
                    i = i * 2 + 1
                else:
                    next_b = bi
                    next_num = ni
                    dst_char = labels[i:i+1]
                    i = i * 2 + 2
            if next_b == 0 or dst_char is None:
                return b""
            return dst_char + self._get_word_node(offset, next_b, index - next_num)
        else: # PREFIX
            header = self.data[offset]
            p_len = header >> 1
            raw_ptr = self.data[offset + 1 : offset + 4]
            next_ptr = int.from_bytes(raw_ptr, "big", signed=True)
            prefix = self.data[offset + 4 : offset + 4 + p_len]
            return prefix + self._get_word_node(offset, next_ptr, index)

    def query(self, dname, word: str):
        d = self.dicts[dname]
        wb = word.encode("utf-8")
        found, index = self.find_node(0, d["root_ptr"], wb, 0)
        if not found:
            return False, None, None
        alias_idx = self.resolve_alias(dname, index)
        target_idx = alias_idx if alias_idx >= 0 else index
        target_word = self.get_word_at_index(dname, target_idx).decode("utf-8", errors="replace")
        return True, index, target_word

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    cd = CDict(Path(r"E:\Development\AndroidApp\NHSCustomKeyboard\assets\dictionaries\en_US.dict").read_bytes())
    print("Testing en_US emoji:")
    for query in ["love", "smile", "heart", "cat", "dog"]:
        found, idx, target = cd.query("emoji", query)
        print(f"  query('{query}') -> found={found}, target={target}")
