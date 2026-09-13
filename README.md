# bn.dict Developer Workspace

This folder contains the complete source files, emoji mapping rules, and build pipeline for developing, updating, and compiling **`bn.dict`** (the Bengali vocabulary and emoji dictionary) for **OsthirKeyboard / NHSCustomKeyboard**.

---

## Directory Structure

```text
E:\Development\AndroidApp\bn.dict\
  ├── sources\
  │   ├── bangla_words.combined    # Bengali vocabulary with frequencies (f=1..255)
  │   ├── bangla_emojis.combined   # Bangla/Banglish/English -> Emoji shortcut mappings
  │   └── subst.json               # Character / diacritic substitution rules
  ├── scripts\
  │   ├── build.py                 # Main build script (compiles & auto-deploys to app)
  │   └── wordlist_merger.py       # Helper to convert raw text wordlists into .combined format
  ├── output\                      # Output folder containing generated bn.dict
  ├── build.ps1                    # 1-Click PowerShell build runner
  └── README.md                    # Documentation & workflow guide
```

---

## How it Works

1. **`main` Sub-Dictionary**:
   - Stored in `sources/bangla_words.combined`.
   - Contains Bengali words with frequency weighting ($f=1\dots255$).
   - Used by the keyboard engine for spell check, auto-completion, and suggestion bar.

2. **`emoji` Sub-Dictionary**:
   - Stored in `sources/bangla_emojis.combined`.
   - Maps English words (`love`), Phonetic Banglish (`valobasa`), and Bengali Unicode script (`ভালবাসা`) to the same target emoji (`❤️`).
   - Used by the keyboard engine for instant emoji suggestions as you type.

---

## How to Add New Words or Emojis

### 1. Adding New Bengali Words:
Open `sources/bangla_words.combined` and add:
```text
word=আপনার_নতুন_শব্দ,f=220
```

### 2. Adding New Emoji Shortcuts:
Open `sources/bangla_emojis.combined` and add:
```text
# Word with shortcut emoji
word=love,f=14,not_a_word=true
 shortcut=❤️,f=14

word=valobasa,f=14,not_a_word=true
 shortcut=❤️,f=14

word=ভালবাসা,f=14,not_a_word=true
 shortcut=❤️,f=14
```

---

## How to Build and Deploy `bn.dict`

### Option 1: Run with PowerShell (Windows)
```powershell
.\build.ps1
```

### Option 2: Run with Python
```bash
python scripts/build.py
```

The build script will:
1. Validate your `.combined` files for syntax errors.
2. Compile `bn.dict` using the integrated Python compiler (or `cdict-tool` if installed) with both `main:` and `emoji:` sub-dictionaries.
3. Automatically verify vocabulary and emoji shortcuts.
4. Output the compiled binary to `output/bn.dict`.
5. (Optional) Deploy directly to any custom path using:
   `python scripts/build.py --deploy path/to/assets/dictionaries/`

---

## Compiler Details

`bn.dict` is powered by a zero-dependency native Python compiler (`scripts/cdict_compiler.py`) compatible with `libcdict` Format Version 1. No OCaml, opam, or dune setup is required. If a native `cdict-tool` binary is present, the script can seamlessly use either.
