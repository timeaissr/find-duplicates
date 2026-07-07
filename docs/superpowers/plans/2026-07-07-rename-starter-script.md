# Rename Starter Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename `find_duplicates_xxh3_128.py` to `find_duplicates.py` and update documentation references.

**Architecture:** Replace the physical wrapper script in the root directory and update all of its references in `README.md`.

**Tech Stack:** Python 3.12, Git

## Global Constraints

- Python >= 3.12
- Keep changes minimal and clean.
- Update references in README.md.

---

### Task 1: Rename the starter script

**Files:**
- Create: `find_duplicates.py`
- Delete: `find_duplicates_xxh3_128.py`

**Interfaces:**
- Consumes: None
- Produces: `find_duplicates.py` executable script

- [ ] **Step 1: Create the new file `find_duplicates.py`**

Write the following content to `find_duplicates.py`:
```python
from find_duplicates.cli import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
```

- [ ] **Step 2: Delete `find_duplicates_xxh3_128.py`**

Remove the file `find_duplicates_xxh3_128.py`.

- [ ] **Step 3: Run the new script to verify it works**

Run: `python find_duplicates.py --help`
Expected: Outputs command-line argument instructions for `find-duplicates`.

- [ ] **Step 4: Commit the renaming changes**

Run:
```bash
git add find_duplicates.py
git rm find_duplicates_xxh3_128.py
git commit -m "feat: rename find_duplicates_xxh3_128.py to find_duplicates.py"
```

### Task 2: Update README.md references

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: `find_duplicates.py` (created in Task 1)
- Produces: Updated `README.md`

- [ ] **Step 1: Modify `README.md` to update references**

In `README.md` (lines 30 and 79), change:
`find_duplicates_xxh3_128.py`
to:
`find_duplicates.py`

- [ ] **Step 2: Run git diff to check changes**

Run: `git diff README.md`
Expected: Outputs diff showing the renamed script references in the ASCII folder structure and execution example.

- [ ] **Step 3: Commit changes**

Run:
```bash
git add README.md
git commit -m "docs: update README references to find_duplicates.py"
```
