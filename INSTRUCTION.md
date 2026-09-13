# Step-by-Step Developer Instructions (`INSTRUCTION.md`)

This guide provides practical instructions for managing, building, testing, and troubleshooting the **`bn.dict`** dictionary engine for **OsthirKeyboard**.

---

## Table of Contents
1. [Prerequisites & Environment Setup](#1-prerequisites--environment-setup)
2. [Step 1: Adding & Editing Bengali Vocabulary](#2-step-1-adding--editing-bengali-vocabulary)
3. [Step 2: Adding & Managing Emoji Shortcuts](#3-step-2-adding--managing-emoji-shortcuts)
4. [Step 3: Importing Large Wordlists from External Corpora](#4-step-3-importing-large-wordlists-from-external-corpora)
5. [Step 4: Compiling `bn.dict` with `cdict-tool`](#5-step-4-compiling-bndict-with-cdict-tool)
6. [Step 5: Testing & Querying the Compiled Dictionary](#6-step-5-testing--querying-the-compiled-dictionary)
7. [Step 6: Deploying to the Keyboard App](#7-step-6-deploying-to-the-keyboard-app)
8. [Troubleshooting & FAQ](#8-troubleshooting--faq)

---

## 1. Prerequisites & Environment Setup

### Tools Needed:
- **Python 3.8+**: For automation scripts (`build.py`, `wordlist_merger.py`).
- **`cdict-tool`**: The binary dictionary compiler (located in `NHSCustomKeyboard/vendor/cdict`).
- **PowerShell** (Windows) or **Bash** (Linux/WSL/macOS).

### Compiling `cdict-tool` (If not already compiled):
`cdict-tool` is written in OCaml. To build the executable:

#### On Linux / WSL / macOS:
```bash
# 1. Install OCaml package manager (opam) and dune
sudo apt install opam    # On Ubuntu/Debian
opam init
eval $(opam env)
opam install dune

# 2. Build cdict-tool
cd ../NHSCustomKeyboard/vendor/cdict
dune build
```
The compiled executable will be at `_build/default/cdict-tool/main.exe`.

---

## 2. Step 1: Adding & Editing Bengali Vocabulary

All Bengali words for spell checking and autocomplete suggestions live in:
📄 `sources/bangla_words.combined`

### Syntax Rules:
1. Every entry starts with `word=`:
   ```text
   word=বাংলা_শব্দ,f=240
   ```
2. **Frequency Score (`f=`)**: Must be an integer between `1` and `255`:
   - `250 - 255`: Ultra common pronouns, conjunctions, and greetings (`আমি`, `তুমি`, `না`, `হ্যাঁ`, `ভালো`).
   - `200 - 249`: Common daily conversation vocabulary (`ধন্যবাদ`, `ভালোবাসা`, `কাজ`, `টাকা`, `বন্ধু`).
   - `150 - 199`: Less frequent words, names, places (`ময়মনসিংহ`, `বিশ্ববিদ্যালয়`).
   - `1 - 149`: Rare or technical words.
3. Keep words sorted alphabetically or by frequency for maintainability.

---

## 3. Step 2: Adding & Managing Emoji Shortcuts

Emoji keyword triggers live in:
📄 `sources/bangla_emojis.combined`

### How to Map Multiple Words to the Same Emoji:
To make `love`, `valobasa`, `bhalobasha`, and `ভালবাসা` all trigger ❤️:

```text
# English word
word=love,f=14,not_a_word=true
 shortcut=❤️,f=14

# Banglish Phonetic words
word=valobasa,f=14,not_a_word=true
 shortcut=❤️,f=14
word=bhalobasha,f=14,not_a_word=true
 shortcut=❤️,f=14
word=prem,f=14,not_a_word=true
 shortcut=❤️,f=14

# Native Bengali Script words
word=ভালবাসা,f=14,not_a_word=true
 shortcut=❤️,f=14
word=ভালোবাসা,f=14,not_a_word=true
 shortcut=❤️,f=14
word=প্রেম,f=14,not_a_word=true
 shortcut=❤️,f=14
```

> **Note**: `not_a_word=true` prevents the emoji alias keyword from polluting normal text suggestions if it's not a real word.

---

## 4. Step 3: Importing Large Wordlists from External Corpora

If you have a plain text file of words (`my_words.txt`) or frequency lists:

```bash
# Convert raw text wordlist to .combined format with default frequency 200
python scripts/wordlist_merger.py my_words.txt sources/imported_words.combined --default-freq 200
```

You can then merge or copy the entries into `sources/bangla_words.combined`.

---

## 5. Step 4: Compiling `bn.dict` with `cdict-tool`

### 1-Click Build:
Run from PowerShell:
```powershell
.\build.ps1
```
Or with Python:
```bash
python scripts/build.py
```

### Manual Compilation Command:
```bash
cdict-tool build -o output/bn.dict \
    main:sources/bangla_words.combined \
    emoji:sources/bangla_emojis.combined
```

---

## 6. Step 5: Testing & Querying the Compiled Dictionary

Before deploying, verify that queries and emoji shortcuts work correctly:

```bash
# Test exact word lookup
cdict-tool query output/bn.dict আমি

# Test prefix lookup
cdict-tool query output/bn.dict ভাল

# Test Banglish emoji lookup
cdict-tool query output/bn.dict valobasa
# Expected Output: found: "❤️"

# Test Bengali script emoji lookup
cdict-tool query output/bn.dict ভালোবাসা
# Expected Output: found: "❤️"
```

---

## 7. Step 6: Deploying to the Keyboard App

By default, `scripts/build.py` outputs the compiled binary to `output/bn.dict`.

To copy the dictionary to your keyboard project:
```bash
# Option A: Specify destination path
python scripts/build.py --deploy ../NHSCustomKeyboard/assets/dictionaries/

# Option B: Manually copy output/bn.dict to your app assets
cp output/bn.dict ../NHSCustomKeyboard/assets/dictionaries/bn.dict
```

When you launch or rebuild the Android app:
1. `Dictionaries.java` detects `assets/dictionaries/bn.dict`.
2. It installs and caches the dictionary in internal storage.
3. `Suggestions.java` immediately queries both Bengali vocabulary and emoji shortcuts!

---

## 8. Troubleshooting & FAQ

### Q1: `cdict-tool` not found error?
- Ensure you have built `cdict-tool` inside `../NHSCustomKeyboard/vendor/cdict` using `dune build`, or put `cdict-tool.exe` in your system `PATH`.

### Q2: Words with spaces or punctuation?
- Single dictionary entries must be single words without spaces. For phrases like "ঠিক আছে", use underscores in the emoji file: `word=thik_ache` and `word=ঠিক_আছে`.

### Q3: How to test on device?
- Run `./gradlew assembleDebug` in `NHSCustomKeyboard` and install the APK on your device.
