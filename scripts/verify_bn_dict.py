import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cdict_engine import CDict

sys.stdout.reconfigure(encoding="utf-8")

def normalize_bengali(text: str) -> str:
    import unicodedata
    t = unicodedata.normalize('NFC', text.strip())
    t = t.replace('\u09a1\u09bc', '\u09dc')  # ড + ় -> ড়
    t = t.replace('\u09a2\u09bc', '\u09dd')  # ঢ + ় -> ঢ়
    t = t.replace('\u09af\u09bc', '\u09df')  # য + ় -> য়
    return t

def verify():
    dict_path = Path("output/bn.dict")
    assert dict_path.exists(), "output/bn.dict does not exist!"
    
    cd = CDict(dict_path.read_bytes())
    print("=== Testing main dictionary ===")
    test_words = [
        # Baseline core vocabulary
        ("আমি", True),
        ("তুমি", True),
        ("ভালোবাসা", True),
        ("বাংলাদেশ", True),
        ("ধন্যবাদ", True),
        ("মা", True),
        ("বাবা", True),
        # MinhasKamal BengaliDictionary & WordLists
        ("অংশীদার", True),
        ("বাগ্দান", True),
        ("সুদক্ষ", True),
        ("অম্লীকরণ", True),
        ("সঠিকতা", True),
        # Foysal87 Root words & NLP datasets
        ("অপনীত", True),
        ("অংশক", True),
        ("অঞ্জলি", True),
        # Inflected & compound forms
        ("অঙ্গপ্রতিষ্ঠানগুলো", True),
        ("অঙ্গসংগঠনগুলোর", True),
        ("অঙ্গপ্রতিষ্ঠানে", True),
        ("উপজেলার", True),
        ("ছাত্রীরাও", True),
        # Nukta recomposed words (ড়, ঢ়, য়)
        ("হয়ে", True),
        ("হয়েছে", True),
        ("বাড়ি", True),
        ("দৃঢ়", True),
        ("বাঙালি", True),
        # Number words
        ("একশ", True),
        ("হাজার", True),
        ("কোটি", True),
        # Negative test cases (corrupted virama-stripped words & non-words)
        ("মধযে", False),
        ("জনয", False),
        ("হযে", False),
        ("অবাকশব্দ", False),
        ("কখগঘঙ", False)
    ]
    passed = 0
    for raw_w, expected in test_words:
        w = normalize_bengali(raw_w)
        found, idx, target = cd.query("main", w)
        status = "✓ PASS" if found == expected else "✗ FAIL"
        print(f"  {status}: Word '{raw_w}' -> found={found} (expected {expected})")
        assert found == expected, f"Failed word check for {raw_w}"
        passed += 1
    print(f"[+] All {passed} vocabulary checks passed successfully!")

    print("\n=== Testing emoji dictionary shortcuts ===")
    test_emojis = [
        ("love", "❤️"),
        ("valobasa", "❤️"),
        ("ভালবাসা", "❤️"),
        ("prem", "❤️"),
        ("প্রেম", "❤️"),
        ("hridoy", "❤️"),
        ("হৃদয়", "❤️"),
        ("কলিজা", "❤️"),
        ("jaan", "❤️"),
        ("valobasi", "💕"),
        ("ভালোবাসি", "💕"),
        ("দুই_মন", "💕"),
        ("crush", "💖"),
        ("kosto", "💔"),
        ("মনভাঙা", "💔"),
        ("dhoka", "💔"),
        ("হাসি", "😂"),
        ("lol", "😂"),
        ("haste_haste_sesh", "😂"),
        ("khushi", "😀"),
        ("মুচকি_হাসি", "😀"),
        ("osthir", "😎"),
        ("অস্থির", "😎"),
        ("agun", "🔥"),
        ("আগুন", "🔥"),
        ("chorom", "🔥"),
        ("chomor", "🔥"),
        ("party", "🥳"),
        ("শুভ_জন্মদিন", "🥳"),
        ("eksho", "💯"),
        ("১০০", "💯"),
        ("magic", "✨"),
        ("চকচক", "✨"),
        ("cry", "😭"),
        ("কান্না", "😭"),
        ("sad", "😢"),
        ("মন_খারাপ", "😢"),
        ("rag", "😡"),
        ("রাগ", "😡"),
        ("চুমু", "😘"),
        ("kiss", "😘"),
        ("ফিদা", "😍"),
        ("sundor", "😍"),
        ("চোখ_মারা", "😉"),
        ("লজ্জা", "😅"),
        ("ধুর", "🙄"),
        ("চিন্তা", "🤔"),
        ("morlam", "💀"),
        ("like", "👍"),
        ("ভালো", "👍"),
        ("dislike", "👎"),
        ("খারাপ", "👎"),
        ("ok", "👌"),
        ("সঠিক", "👌"),
        ("peace", "✌️"),
        ("জয়", "✌️"),
        ("pray", "🙏"),
        ("দোয়া", "🙏"),
        ("ধন্যবাদ", "🙏"),
        ("friend", "🤝"),
        ("বন্ধু", "🤝"),
        ("clap", "👏"),
        ("তালি", "👏"),
        ("shokti", "💪"),
        ("শক্তি", "💪"),
        ("bye", "👋"),
        ("টাটা", "👋"),
        ("cha", "☕"),
        ("চা", "☕"),
        ("khabar", "🍔"),
        ("খাবার", "🍔"),
        ("pizza", "🍕"),
        ("পিজ্জা", "🍕"),
        ("chocolate", "🍫"),
        ("মিষ্টি", "🍫"),
        ("aam", "🥭"),
        ("আম", "🥭"),
        ("birthday", "🎂"),
        ("জন্মদিন", "🎂"),
        ("taka", "💰"),
        ("টাকা", "💰"),
        ("dollar", "💵"),
        ("ডলার", "💵"),
        ("sun", "☀️"),
        ("সূর্য", "☀️"),
        ("chand", "🌙"),
        ("চাঁদ", "🌙"),
        ("star", "⭐"),
        ("তারা", "⭐"),
        ("rain", "🌧️"),
        ("badol", "🌧️"),
        ("বৃষ্টি", "🌧️"),
        ("rose", "🌹"),
        ("গোলাপ", "🌹"),
        ("sleep", "😴"),
        ("ঘুম", "😴"),
        ("car", "🚗"),
        ("গাড়ি", "🚗"),
        ("bike", "🏍️"),
        ("বাইক", "🏍️"),
        ("football", "⚽"),
        ("খেলা", "⚽"),
        ("cricket", "🏏"),
        ("ক্রিকেট", "🏏"),
        ("bhat", "🍚"),
        ("ভাত", "🍚"),
        ("mach", "🐟"),
        ("মাছ", "🐟"),
        ("biral", "🐈"),
        ("বিড়াল", "🐈"),
        ("kukur", "🐕"),
        ("কুকুর", "🐕"),
        ("bagh", "🐅"),
        ("বাঘ", "🐅"),
        ("bangladesh", "🇧🇩"),
        ("বাংলাদেশ", "🇧🇩"),
        ("palestine", "🇵🇸"),
        ("ফিলিস্তিন", "🇵🇸"),
        ("saudi", "🇸🇦"),
        ("সৌদি_আরব", "🇸🇦"),
        ("argentina", "🇦🇷"),
        ("আর্জেন্টিনা", "🇦🇷"),
        ("brazil", "🇧🇷"),
        ("ব্রাজিল", "🇧🇷"),
        ("india", "🇮🇳"),
        ("ভারত", "🇮🇳"),
        ("pakistan", "🇵🇰"),
        ("পাকিস্তান", "🇵🇰"),
        ("turkey", "🇹🇷"),
        ("তুরস্ক", "🇹🇷"),
        ("usa", "🇺🇸"),
        ("আমেরিকা", "🇺🇸"),
        ("uk", "🇬🇧"),
        ("যুক্তরাজ্য", "🇬🇧"),
        ("japan", "🇯🇵"),
        ("জাপান", "🇯🇵"),
        ("germany", "🇩🇪"),
        ("জার্মানি", "🇩🇪"),
        ("france", "🇫🇷"),
        ("ফ্রান্স", "🇫🇷"),
        ("spain", "🇪🇸"),
        ("স্পেন", "🇪🇸"),
        ("portugal", "🇵🇹"),
        ("পর্তুগাল", "🇵🇹"),
        ("qatar", "🇶🇦"),
        ("কাতার", "🇶🇦"),
        ("dubai", "🇦🇪"),
        ("দুবাই", "🇦🇪"),
    ]
    for kw, expected_emoji in test_emojis:
        found, idx, target = cd.query("emoji", kw)
        print(f"  Keyword '{kw}': found={found}, emoji='{target}' (expected '{expected_emoji}')")
        assert found is True, f"Failed emoji query for {kw}"
        assert target == expected_emoji, f"Expected {expected_emoji}, got {target} for {kw}"

    print("\n[✓] ALL TESTS PASSED! bn.dict is 100% valid and working.")

if __name__ == "__main__":
    verify()
