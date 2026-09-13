#!/usr/bin/env python3
"""
English Dataset Acquisition Script for Next-Word Prediction
Downloads high-quality public English corpora:
1. Peter Norvig's Web Trillion Word Bigrams (Google Web 1T)
2. Stanford Alpaca English Instruction & Conversation Dataset
"""

import os
import sys
import urllib.request
from pathlib import Path

# Ensure UTF-8 stdout
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_ENGLISH_DIR = ROOT_DIR / "raw_data_sources" / "english"
RAW_ENGLISH_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

DATASETS = [
    {
        "name": "count_2w.txt",
        "url": "https://norvig.com/ngrams/count_2w.txt",
        "description": "Peter Norvig's Web Trillion Word 2-gram frequencies (Google Web 1T)",
        "min_size": 4_000_000,
    },
    {
        "name": "alpaca_data.json",
        "url": "https://raw.githubusercontent.com/tatsu-lab/stanford_alpaca/main/alpaca_data.json",
        "description": "Stanford Alpaca 52k conversational and instructional dataset",
        "min_size": 20_000_000,
    },
]

def download_file(url: str, dest_path: Path, min_size: int, description: str):
    if dest_path.exists() and dest_path.stat().st_size >= min_size:
        print(f"[i] Already exists: {dest_path.name} ({dest_path.stat().st_size:,} bytes) - {description}")
        return True

    print(f"[*] Downloading: {dest_path.name} from {url}...")
    print(f"    Target: {description}")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=120) as resp:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            block_size = 1024 * 64

            with open(dest_path, "wb") as f:
                while True:
                    chunk = resp.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        print(f"\r    Progress: {downloaded:,} / {total_size:,} bytes ({pct:.1f}%)", end="", flush=True)
                    else:
                        print(f"\r    Progress: {downloaded:,} bytes", end="", flush=True)
            print()

        actual_size = dest_path.stat().st_size
        print(f"[+] Download complete: {dest_path.name} ({actual_size:,} bytes)")
        return True
    except Exception as e:
        print(f"\n[-] Failed to download {dest_path.name}: {e}")
        if dest_path.exists():
            dest_path.unlink()
        return False

def download_all():
    print("=" * 60)
    print("  Downloading English Datasets for Next-Word Prediction")
    print("=" * 60)
    success = True
    for item in DATASETS:
        dest = RAW_ENGLISH_DIR / item["name"]
        ok = download_file(item["url"], dest, item["min_size"], item["description"])
        if not ok:
            success = False

    if success:
        print("\n[✓] All English datasets successfully downloaded and verified.")
    else:
        print("\n[!] One or more datasets could not be downloaded.")
    return success

if __name__ == "__main__":
    download_all()
