# OfferLog

OfferLog is an automated Python tool that connects to your Gmail, extracts job application updates using large language models (LLMs) via OpenRouter, and logs the structured data directly into a Google Sheet. It runs on a schedule to keep your job hunt organized with zero manual data entry.

## Features & Optimizations
- **Smart Parsing**: Uses LLMs to accurately extract company name, role, status, and next steps from unstructured emails.
- **Cost-Efficient**: Defaults to free or extremely cheap models on OpenRouter to keep operating costs near zero.
- **Optimized API Usage**: 
  - Uses `batchGet` for Google Sheets to minimize read requests and prevent rate-limiting.
  - Dynamically tracks the last successful run time to fetch only new emails.
  - Deduplicates by Message ID to prevent wasteful LLM re-processing.
- **Robust Error Handling**: Implements exponential backoff for network issues and API rate limits.

## Prerequisites

Before installing, you need to set up the necessary API keys and credentials:

1. **Google Cloud Credentials**: 
   - You need a `credentials.json` file authorized for Gmail (Read-only) and Google Sheets API.
   - [How to get Google Cloud credentials](https://developers.google.com/workspace/guides/create-credentials)
2. **OpenRouter API Key**: 
   - Used for LLM parsing. 
   - [Get an OpenRouter API key](https://openrouter.ai/)
3. **Gmail Label Setup**:
   - The script is highly optimized to search exclusively for emails with the `JobHunt` label. You must create this label and set up a filter to auto-tag incoming job emails.
   - [How to create labels and filters in Gmail](https://support.google.com/mail/answer/118708?hl=en)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/OfferLog.git
   cd OfferLog
   ```

2. **Install Dependencies**:
   This project uses `uv` for fast dependency management.
   ```bash
   uv sync --frozen
   ```

3. **Configure Environment Variables**:
   Copy the example environment file and update it:
   ```bash
   cp .env.example .env
   ```
   Add your `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` (e.g., `google/gemini-2.0-flash-lite-preview-02-05:free`), and `SPREADSHEET_ID`.

4. **Add Google Credentials**:
   Create a `credentials/` directory in the project root and place your `credentials.json` file inside it.

## Usage

Run the script manually:
```bash
uv run python main.py
```

On the first run, the script will prompt you to authenticate via your browser to generate `gmail_token.json` and `sheets_token.json`. It will also automatically create a new Google Sheet if a `SPREADSHEET_ID` is not provided in your `.env` file.

### Automated Runs (GitHub Actions)
The project includes a GitHub Actions workflow (`.github/workflows/run.yml`) configured to run every 12 hours. 

To enable this, you must add your credentials as **Repository Secrets**:
1. Go to your repository on GitHub.
2. Click **Settings** > **Secrets and variables** > **Actions**.
3. Click **New repository secret** and add the following exactly as named:

- `GOOGLE_CREDENTIALS_JSON`: Paste the entire contents of your local `credentials/credentials.json`.
- `GMAIL_TOKEN_JSON`: Paste the entire contents of your local `credentials/gmail_token.json` (generated after running locally once).
- `SHEETS_TOKEN_JSON`: Paste the entire contents of your local `credentials/sheets_token.json` (generated after running locally once).
- `OPENROUTER_API_KEY`: Your OpenRouter API key.
- `SPREADSHEET_ID`: The ID of your Google Sheet.

The action leverages `uv` and GitHub caching, so dependencies install in seconds, saving precious Actions runner time.
