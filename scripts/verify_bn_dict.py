import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cdict_engine import CDict

sys.stdout.reconfigure(encoding="utf-8")

def verify():
    dict_path = Path("output/bn.dict")
    assert dict_path.exists(), "output/bn.dict does not exist!"
    
    cd = CDict(dict_path.read_bytes())
    print("=== Testing main dictionary ===")
    test_words = [
        ("আমি", True),
        ("তুমি", True),
        ("ভালোবাসা", True),
        ("বাংলাদেশ", True),
        ("ধন্যবাদ", True),
        ("অবাকশব্দ", False)
    ]
    for w, expected in test_words:
        found, idx, target = cd.query("main", w)
        print(f"  Word '{w}': found={found} (expected {expected}), target='{target}'")
        assert found == expected, f"Failed word check for {w}"

    print("\n=== Testing emoji dictionary shortcuts ===")
    test_emojis = [
        ("love", "❤️"),
        ("valobasa", "❤️"),
        ("ভালবাসা", "❤️"),
        ("prem", "❤️"),
        ("প্রেম", "❤️"),
        ("hridoy", "❤️"),
        ("হৃদয়", "❤️"),
        ("crush", "💖"),
        ("kosto", "💔"),
        ("মনভাঙা", "💔"),
    ]
    for kw, expected_emoji in test_emojis:
        found, idx, target = cd.query("emoji", kw)
        print(f"  Keyword '{kw}': found={found}, emoji='{target}' (expected '{expected_emoji}')")
        assert found is True, f"Failed emoji query for {kw}"
        assert target == expected_emoji, f"Expected {expected_emoji}, got {target} for {kw}"

    print("\n[✓] ALL TESTS PASSED! bn.dict is 100% valid and working.")

if __name__ == "__main__":
    verify()
