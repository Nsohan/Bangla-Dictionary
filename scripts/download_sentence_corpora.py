import os
import sys
import json
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

RAW_SENTENCES_DIR = Path(__file__).resolve().parent.parent / "raw_data_sources" / "sentences"
RAW_SENTENCES_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

DATASETS = [
    {
        "name": "alpaca_bangla_18k.json",
        "url": "https://huggingface.co/datasets/nihalbaig/alpaca_bangla/resolve/main/translated_18k.json"
    },
    {
        "name": "banglarqa_train.json",
        "url": "https://huggingface.co/datasets/sartajekram/BanglaRQA/resolve/main/Train.json"
    },
    {
        "name": "banglarqa_val.json",
        "url": "https://huggingface.co/datasets/sartajekram/BanglaRQA/resolve/main/Validation.json"
    },
    {
        "name": "banglarqa_test.json",
        "url": "https://huggingface.co/datasets/sartajekram/BanglaRQA/resolve/main/Test.json"
    }
]

def download_all():
    print("=== Downloading Bengali Sentence Corpora ===")
    for item in DATASETS:
        dest = RAW_SENTENCES_DIR / item["name"]
        if dest.exists() and dest.stat().st_size > 1000:
            print(f"[i] Already exists: {dest.name} ({dest.stat().st_size} bytes)")
            continue
        print(f"[*] Downloading {item['name']} from {item['url']}...")
        try:
            req = urllib.request.Request(item["url"], headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp, open(dest, 'wb') as f:
                content = resp.read()
                f.write(content)
            print(f"[+] Saved {dest.name} ({len(content)} bytes)")
        except Exception as e:
            print(f"[-] Error downloading {item['name']}: {e}")

if __name__ == "__main__":
    download_all()
