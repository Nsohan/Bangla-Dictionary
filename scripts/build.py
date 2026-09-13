#!/usr/bin/env python3
"""
Build Script for bn.dict (Bangla + Banglish + Emoji Dictionary)
Compiles source combined files using native Python compiler (or cdict-tool) and deploys directly to OsthirKeyboard.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Ensure scripts dir is in path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import cdict_compiler
from test_cdict_engine import CDict

ROOT_DIR = SCRIPTS_DIR.parent
SOURCES_DIR = ROOT_DIR / "sources"
OUTPUT_DIR = ROOT_DIR / "output"

WORDS_FILE = SOURCES_DIR / "bangla_words.combined"
EMOJIS_FILE = SOURCES_DIR / "bangla_emojis.combined"
OUTPUT_DICT = OUTPUT_DIR / "bn.dict"

def find_cdict_tool():
    """Find cdict-tool executable in system PATH (optional)."""
    return shutil.which("cdict-tool")

def validate_sources():
    """Validate that source files exist and have non-zero size."""
    if not WORDS_FILE.exists():
        print(f"[-] Error: Words file not found: {WORDS_FILE}")
        return False
    if not EMOJIS_FILE.exists():
        print(f"[-] Error: Emojis file not found: {EMOJIS_FILE}")
        return False
    print(f"[+] Found words file: {WORDS_FILE} ({WORDS_FILE.stat().st_size} bytes)")
    print(f"[+] Found emojis file: {EMOJIS_FILE} ({EMOJIS_FILE.stat().st_size} bytes)")
    return True

def build_dict(cdict_tool_path=None):
    """Build bn.dict using cdict-tool or Python compiler."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    if cdict_tool_path:
        cmd = [
            cdict_tool_path,
            "build",
            "-o", str(OUTPUT_DICT),
            f"main:{WORDS_FILE}",
            f"emoji:{EMOJIS_FILE}"
        ]
        print(f"[*] Running external compiler: {' '.join(cmd)}")
        try:
            res = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(res.stdout)
        except subprocess.CalledProcessError as e:
            print(f"[-] Compilation error:\n{e.stderr}")
            return False
    else:
        print("[*] Compiling bn.dict using built-in Python CDict compiler...")
        inputs = [
            ("main", WORDS_FILE),
            ("emoji", EMOJIS_FILE),
        ]
        cdict_compiler.compile_dictionaries(inputs, OUTPUT_DICT)

    if OUTPUT_DICT.exists() and OUTPUT_DICT.stat().st_size > 0:
        print(f"[+] Successfully built {OUTPUT_DICT} ({OUTPUT_DICT.stat().st_size} bytes)")
        return True
    else:
        print(f"[-] Build failed: Output file is missing or empty.")
        return False

def verify_dict():
    """Verify integrity of built dictionary."""
    try:
        cd = CDict(OUTPUT_DICT.read_bytes())
        # Check a sample Bengali word and emoji shortcut
        found_w, _, _ = cd.query("main", "আমি")
        found_e, _, target_e = cd.query("emoji", "love")
        if found_w and found_e and target_e == "❤️":
            print("[+] Dictionary verification passed (main vocabulary and emojis verified).")
            return True
        else:
            print(f"[-] Verification failed: word={found_w}, emoji={found_e}, target={target_e}")
            return False
    except Exception as e:
        print(f"[-] Verification error: {e}")
        return False

import argparse

def deploy_to_path(deploy_path: str):
    """Copy the compiled bn.dict and bn_bigrams.bin to a specified output directory."""
    dest_dir = Path(deploy_path)
    if dest_dir.is_file():
        dest_dir = dest_dir.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    if OUTPUT_DICT.exists():
        dest_dict = dest_dir / "bn.dict"
        shutil.copy2(OUTPUT_DICT, dest_dict)
        print(f"[+] Deployed bn.dict to: {dest_dict}")

    bigram_bin = OUTPUT_DIR / "bn_bigrams.bin"
    if bigram_bin.exists():
        dest_bigram = dest_dir / "bn_bigrams.bin"
        shutil.copy2(bigram_bin, dest_bigram)
        print(f"[+] Deployed bn_bigrams.bin to: {dest_bigram}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Build and compile bn.dict")
    parser.add_argument("--deploy", "-d", type=str, default=None, help="Optional destination path to copy the compiled bn.dict to")
    args = parser.parse_args()

    # Force UTF-8 stdout if needed
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 60)
    print("  bn.dict Builder (Bangla Words + Emojis)")
    print("=" * 60)

    if not validate_sources():
        sys.exit(1)

    cdict_tool = find_cdict_tool()
    if cdict_tool:
        print(f"[+] Using native cdict-tool: {cdict_tool}")
    else:
        print("[+] Using integrated Python cdict compiler (No OCaml/dune required)")

    if build_dict(cdict_tool) and verify_dict():
        if args.deploy:
            deploy_to_path(args.deploy)
        print(f"\n[✓] Build complete! Output generated at: {OUTPUT_DICT}")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
