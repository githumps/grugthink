# How to Send Grug to New Caves (Deployment)

This stone tells how to make Grug live in a new cave (server). Grug needs a magic box (Docker) to live in. This keeps Grug safe and strong.

## Quick Start: `docker-compose` (Easy Way)

This is the best way to wake Grug. It uses the `docker-compose.yml` magic scroll.

1.  **Get Grug's Code:**
    ```bash
    git clone https://github.com/githumps/grugthink.git
    cd grug-think
    ```

2.  **Tell Grug Secrets:**
    *   Copy `.env.example` to `.env`.
    *   Fill `.env` with your secrets. You need `DISCORD_TOKEN` and a thinking spirit (like `GEMINI_API_KEY`).
    *   **Important**: Set `GRUGBOT_DATA_DIR=/data` in your `.env` file. This tells Grug to use the safe place for his brain.

3.  **Make Brain Cave:**
    ```bash
    mkdir grug-data
    ```

4.  **Wake Grug Up:**
    ```bash
    docker-compose up -d
    ```

Grug is now alive! To put Grug to sleep, use `docker-compose down`.

## One-Liner `docker run` (Hard Way)

If you no have `docker-compose`, you can use this long magic spell.

```bash
docker run -d --name grug-bot --env-file .env -v "$(pwd)/grug-data:/data" ghcr.io/grugthink/grugthink:latest
```

*   This assumes you have a `.env` file with secrets and a `grug-data` folder in the same place.

## How Grug is Made (Release Process)

The tribe chief (author) makes new versions of Grug when Grug learns new tricks. There are two kinds of Grug: **practice Grug** and **great hunt Grug**.

### Practice Grug (Test & Preview Releases)

Before the great hunt, Grug must practice. You make a test Grug to see if he is strong. These are not for other tribes, only for you to test in your own cave.

1.  **Make a Test Box (Test Build):**
    *   Build a magic box with your new code. You can call it `grug-think:test`.
    ```bash
    docker build -t grug-think:test .
    ```
    *   Now you can run this test Grug using the `docker-compose.yml` file. Just change the `image` line to `grug-think:test`.

2.  **Make a Preview Grug (Pre-release):**
    *   Sometimes, the chief wants to show a new Grug before he is ready for the great hunt. This is a preview Grug.
    *   To make one, you make a special mark with `-rc` (Release Candidate) at the end, like `v1.1.0-rc1`.
    ```bash
    git tag -a v1.1.0-rc1 -m "Grug practice for next great hunt."
    git push origin v1.1.0-rc1
    ```
    *   The magic spirit (GitHub Actions) will see this and build a special Grug box. It will be on the GitHub Packages page, but it will not be marked as `latest`. It is a preview for the brave.

### Great Hunt Grug (Official Versioned Releases)

When Grug is strong and ready for all tribes, you make an official Grug. This is a great event.

1.  **Check Grug's Work:** Make sure Grug is strong. All new code must be on the `main` branch. Run the tests one last time.
    *   **Make Magic Air:**
        ```bash
        python3.11 -m venv venv
        ```
    *   **Wake Up Magic Air:**
        ```bash
        source venv/bin/activate
        ```
    *   **Get Tools:**
        ```bash
        pip install -r requirements.txt -r requirements-dev.txt
        ```
    *   **Run Tests:**
        ```bash
        PYTHONPATH=. pytest
        ```

2.  **Make the Official Mark (Git Tag):**
    *   Grug must be marked with a special tag like `v1.0.0` to show he is ready.
    ```bash
    git tag -a v1.0.0 -m "Grug Version 1. Grug is ready for the great hunt."
    git push origin v1.0.0
    ```

3.  **Magic Spirit Does the Rest (GitHub Actions):**
    *   When you push a tag like `v1.0.0`, the magic spirit (GitHub Actions) will automatically:
        *   Create a GitHub Release.
        *   Build the official magic box.
        *   Push the box to GitHub Packages with two names: `ghcr.io/githumps/grugthink:v1.0.0` and `ghcr.io/githumps/grugthink:latest`.

## Grug's Secrets (`.env` file)

Grug needs secrets to know how to think and talk. You put these secrets in a file called `.env`.

| Secret Name          | What It Do                                                              |
| -------------------- | ----------------------------------------------------------------------- |
| `DISCORD_TOKEN`      | Magic key to let Grug into the Discord cave. **(Required)**             |
| `GRUGBOT_VARIANT`    | `prod` for real Grug, `dev` for test Grug.                               |
| `TRUSTED_USER_IDS`   | Who can teach Grug new things. List of user IDs, separated by commas.   |
| `LOG_LEVEL`          | How much Grug talks to himself. `INFO` is normal, `DEBUG` is a lot.     |
| `GEMINI_API_KEY`     | Magic key for Google's thinking spirit.                                 |
| `OLLAMA_URLS`        | Where your own thinking spirits live. Can be many, separated by commas. |
| `GOOGLE_API_KEY`     | Magic key for the magic talking rock (Google Search).                   |
| `GOOGLE_CSE_ID`      | Magic ID for the magic talking rock.                                    |
| `GRUGBOT_DATA_DIR`   | Where Grug keeps his brain. **Set to `/data` for Docker.**              |
