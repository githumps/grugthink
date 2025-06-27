# How to Help Grug (Contributing)

Grug is strong, but Grug can be stronger with help from other cavemen. If you want to help Grug, read these words.

## Before You Start

*   **Talk to Grug First:** If you want to make big changes, talk to the chief (project maintainer) first. Make a new issue on the big rock pile (GitHub Issues) to tell what you want to do. This stops Grug from doing same work twice.

## How to Make Grug Stronger (Development Setup)

1.  **Get Grug's Code:**
    ```bash
    git clone https://github.com/githumps/grugthink.git
    cd grugthink
    ```

2.  **Make Magic Air (Virtual Environment):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Get Tools:** Grug need tools to think and fight.
    ```bash
    pip install -r requirements.txt -r requirements-dev.txt
    ```

4.  **Tell Grug Secrets:** Copy `.env.example` to `.env` and fill it with your test secrets. Set `GRUGBOT_VARIANT=dev` for testing.
    ```bash
    cp .env.example .env
    # Edit .env to set GRUGBOT_VARIANT=dev and add your test DISCORD_TOKEN
    ```

5.  **Wake Grug Up for Testing:**
    ```bash
    python bot.py
    ```

## Sharpen Grug's Spear (Running Tests)

Before you send your changes, make sure Grug's spear is sharp. Run the tests:

```bash
PYTHONPATH=. pytest
```

## Make Grug's Words Clean (Linting)

Grug likes clean words. Make sure your code follows Grug's style:

```bash
ruff check .
ruff format .
```

## How to Give Grug Your Work (Pull Request)

1.  **Make Your Own Branch:** Make a new path for your work.
    ```bash
    git checkout -b my-new-grug-feature
    ```

2.  **Do Your Work:** Make Grug stronger, fix Grug, or teach Grug new tricks.

3.  **Make Small, Clear Marks (Commits):** Each mark should be one small change. Tell Grug what you did.
    ```bash
    git add .
    git commit -m "feat: Grug learn new trick (short message)"
    ```

4.  **Send Your Work to the Big Rock Pile:**
    ```bash
    git push origin my-new-grug-feature
    ```

5.  **Ask Chief to See Your Work (Pull Request):** Go to the big rock pile (GitHub) and make a new Pull Request. Tell the chief what your work does and why Grug needs it.

Thank you for helping Grug!