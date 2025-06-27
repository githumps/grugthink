# Grug's Codex Guide

This guide tells the Codex spirit how Grug likes to work in this cave.

## Dev Environment Tips

*   Grug uses Python 3.11.
*   All dependencies are listed in `requirements.txt` and `requirements-dev.txt`.
*   Grug's brain (database) is `grug_lore.db` and his memory index is `grug_lore.index`.

## Testing Instructions

*   Grug's tests are in the `tests/` folder.
*   To run all tests, use: `PYTHONPATH=. pytest`.
*   Grug likes his words clean. Before making changes, run `ruff check .` and `ruff format .`.
*   Grug also checks for bad spirits in his tools with `pip-audit`.

## PR Instructions

*   **Title Format:** `[<feature/fix/chore>] <Short description of change>`
*   Grug likes small, clear changes. Each commit should do one thing.
*   Make sure all tests pass and words are clean before asking Grug chief to look at your work.

## How Grug Does His Work

*   **Focus:** Grug focuses on the `bot.py`, `grug_db.py`, and `config.py` files for core logic.
*   **Verification:** Grug always runs tests and linting to verify changes.
*   **Error Handling:** Grug likes clear error messages and robust handling of unexpected situations.
*   **Caveman Voice:** When Grug speaks, he speaks like a caveman. Keep this in mind for any new text Grug generates.
