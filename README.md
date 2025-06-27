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
