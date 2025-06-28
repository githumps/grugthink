# Grug Think Bot

Grug bot. Grug see words. Grug say if words TRUE or FALSE. Grug speak like caveman. Grug smart, have big brain and use magic talking rock to find truth.

## What Grug Do

*   **Verify Truth**: Grug listen in cave (Discord). You say words, Grug think hard. Grug say "TRUE" or "FALSE" and give caveman words.
*   **Big Brain**: Grug use big brain (SQLite + FAISS) to remember what he learn.
*   **Magic Talking Rock**: If Grug not know, he ask magic talking rock (Google Search) for answers.
*   **Thinking Spirit**: Grug use thinking spirit (Ollama or Gemini) to make his words.

## How Grug Work

Grug is a Discord bot written in Python. He uses a simple SQLite database to store facts and a FAISS vector index to find relevant information for a given statement. When a user asks Grug to verify something, Grug searches his memory and, if needed, the internet. He then uses a large language model (like Gemini or a local Ollama model) to generate a response in his characteristic caveman-like speech.

## Talk to Grug (Commands)

*   `/verify`: Grug check truth of last message in cave.
*   `/learn`: Teach Grug new fact. (Only for trusted friends).
*   `/what-grug-know`: Grug show you all facts in his brain.
*   `/grug-help`: Grug tell you what he can do.

---

For how to wake Grug up, see `DEPLOYMENT.md`.

## Getting Started

1.  **Make Magic Air (Virtual Environment):**
    ```bash
    python3.11 -m venv venv
    source venv/bin/activate
    ```
2.  **Give Grug Tools:**
    ```bash
    pip install -r requirements.txt -r requirements-dev.txt
    ```
3.  **Check Grug Words:**
    ```bash
    ruff check .
    ruff format .
    ```
4.  **Sharpen Grug Spear:**
    ```bash
    PYTHONPATH=. pytest
    ```

## License and Usage

This project is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE). You may use, modify and share the software for **noncommercial** purposes only. Any kind of commercial use is not permitted.

All libraries listed in `requirements.txt` and `requirements-dev.txt` are distributed under permissive open source licenses such as MIT, BSD or Apache 2.0. These licenses are compatible with the PolyForm Noncommercial terms and may be used within this project so long as their notice requirements are met.
