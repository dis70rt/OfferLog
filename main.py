import os
import re
import json
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from dotenv import load_dotenv
load_dotenv()

from src.gmail_client import GmailClient
from src.openrouter_client import OpenRouterClient
from src.sheets_client import SheetsClient
from src.email_utils import get_email_body
from src.queries import GMAIL_JOB_SEARCH_QUERY

from schemas.schema import OfferRecord, LLMOfferExtraction
from schemas.metadata import AuditRecord

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def log_audit(sheets_client: SheetsClient, spreadsheet_id: str, audit_record: AuditRecord) -> None:
    """Append an AuditRecord to the Audits sheet."""
    sheets_client.append_row(spreadsheet_id, "Audits", [[
        str(audit_record.run_timestamp),
        audit_record.message_id,
        audit_record.generation_id or "",
        audit_record.model or "",
        audit_record.prompt_tokens,
        audit_record.completion_tokens,
        audit_record.reasoning_tokens,
        audit_record.total_tokens,
        audit_record.cost_usd,
        audit_record.status
    ]])


def ensure_spreadsheet(sheets: SheetsClient) -> str | None:
    """
    Ensure the target spreadsheet exists. Creates one with header rows
    if SPREADSHEET_ID is not set, then instructs the user to add it to .env.

    Returns:
        The spreadsheet ID, or None if creation failed or user action is needed.
    """
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    if spreadsheet_id:
        return spreadsheet_id

    logger.info("SPREADSHEET_ID not found in .env. Creating a new spreadsheet...")
    spreadsheet_id = sheets.create_spreadsheet("OfferLog Database")
    if not spreadsheet_id:
        logger.error("Failed to create spreadsheet. Exiting.")
        return None

    sheets.add_worksheet(spreadsheet_id, "Details")
    sheets.add_worksheet(spreadsheet_id, "Audits")

    sheets.append_row(spreadsheet_id, "Details", [[
        "Date Received", "Company", "Role", "Status", "Next Step",
        "Next Step Date", "Email Subject", "Sender", "Message ID", "Thread ID", "Processed At"
    ]])
    sheets.append_row(spreadsheet_id, "Audits", [[
        "Run Timestamp", "Message ID", "Generation ID", "Model",
        "Prompt Tokens", "Completion Tokens", "Reasoning Tokens",
        "Total Tokens", "Cost (USD)", "Status"
    ]])

    logger.info(f"IMPORTANT: Add this to your .env file: SPREADSHEET_ID={spreadsheet_id}")
    logger.info("Run the script again once you've added it.")
    return None


def process_email(
    msg_id: str,
    thread_id: str,
    gmail_svc,
    openrouter: OpenRouterClient,
    sheets: SheetsClient,
    spreadsheet_id: str,
    prompt_template: str,
) -> bool:
    """
    Fetch, parse, and record a single email.

    Returns True if the email was successfully processed and written to Sheets
    (or determined to be irrelevant), False if a retryable failure occurred.
    """
    msg = gmail_svc.users().messages().get(userId='me', id=msg_id, format='full').execute()

    headers = msg['payload'].get('headers', [])
    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), "No Subject")
    sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), "Unknown Sender")
    date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), None)

    date_received = None
    if date_str:
        try:
            # Normalize to UTC before extracting the date to avoid timezone shift edge cases
            date_received = parsedate_to_datetime(date_str).astimezone(timezone.utc).date()
        except Exception as e:
            logger.warning(f"[{msg_id}] Failed to parse date '{date_str}': {e}")

    body = get_email_body(msg['payload'])
    if not body:
        logger.warning(f"[{msg_id}] Could not extract body for '{subject}'. Skipping.")
        return True  # Nothing to retry — permanently skip bodyless emails

    logger.info(f"\n[{msg_id}] Processing: {subject}")

    # Pass instructions purely as the system prompt (preventing prompt injection)
    system_prompt = prompt_template
    
    # Pass user data purely as the user prompt
    user_prompt = f"**Email subject:** {subject}\n**Email sender:** {sender}\n**Email body:**\n{body[:3000]}"

    response_text, raw_metadata = openrouter.generate_text(
        prompt=user_prompt,
        message_id=msg_id,
        system_prompt=system_prompt
    )

    # Convert raw metadata dict back into our domain AuditRecord schema
    audit_record = AuditRecord.from_openrouter_metadata(
        message_id=raw_metadata.get("message_id", msg_id),
        status=raw_metadata.get("status", "unknown"),
        metadata=raw_metadata
    )

    if not response_text:
        logger.error(f"[{msg_id}] Failed to generate response from OpenRouter. Will retry next run.")
        # We DO NOT log_audit here, because if we do, the email's ID will be added to the Audits sheet
        # and the script will skip it forever instead of retrying.
        return False

    # Parse JSON — handle optional markdown fences
    try:
        fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', response_text, re.DOTALL | re.IGNORECASE)
        cleaned_text = fence_match.group(1).strip() if fence_match else response_text.strip()
        parsed_json = json.loads(cleaned_text)
        llm_extraction = LLMOfferExtraction.model_validate(parsed_json)
    except Exception as e:
        logger.error(f"[{msg_id}] Failed to parse JSON response: {e}\nRaw Output: {response_text[:500]}")
        audit_record.status = "parse_error"
        log_audit(sheets, spreadsheet_id, audit_record)
        return False

    if not llm_extraction.relevant:
        logger.info(f"[{msg_id}] Email is not job-related. Skipping.")
        log_audit(sheets, spreadsheet_id, audit_record)
        return True

    offer = OfferRecord(
        **llm_extraction.model_dump(),
        email_subject=subject,
        sender=sender,
        message_id=msg_id,
        thread_id=thread_id,
        date_received=date_received,
        raw_metadata_json=cleaned_text
    )

    logger.info(f"[{msg_id}] Detected Job Update -> Company: {offer.company} | Status: {offer.status}")

    result = sheets.append_row(spreadsheet_id, "Details", [[
        str(offer.date_received) if offer.date_received else "",
        offer.company or "",
        offer.role or "",
        offer.status or "",
        offer.next_step or "",
        str(offer.next_step_date) if offer.next_step_date else "",
        offer.email_subject,
        offer.sender,
        offer.message_id,
        offer.thread_id,
        str(offer.processed_at)
    ]])

    if result is None:
        logger.error(f"[{msg_id}] Failed to write to Sheets. Will retry next run.")
        return False

    log_audit(sheets, spreadsheet_id, audit_record)
    logger.info(f"[{msg_id}] Successfully uploaded to Google Sheets!")
    return True


def main() -> None:
    """
    Main orchestration flow:
    1. Authenticates Google APIs and OpenRouter.
    2. Batch-fetches deduplication state and last run time from Google Sheets.
    3. Queries Gmail for recent job-related emails.
    4. Processes each email via OpenRouter LLM, appending results to Sheets.
    """
    logger.info("Initializing OfferLog Orchestrator...")

    gmail = GmailClient()
    openrouter = OpenRouterClient()
    sheets = SheetsClient()

    spreadsheet_id = ensure_spreadsheet(sheets)
    if not spreadsheet_id:
        return

    try:
        with open("prompts/email_parser.md", "r") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        logger.error("Could not find prompts/email_parser.md. Exiting.")
        return

    # Batch fetch existing message IDs and timestamps from Sheets to save API quota
    try:
        batch_result = sheets.get_service().spreadsheets().values().batchGet(
            spreadsheetId=spreadsheet_id,
            ranges=["Details!I:I", "Audits!B:B", "Audits!A:A"]
        ).execute()
        value_ranges = batch_result.get('valueRanges', [])
        
        details_ids = [row[0] for row in value_ranges[0].get('values', []) if row] if len(value_ranges) > 0 else []
        audits_ids = [row[0] for row in value_ranges[1].get('values', []) if row] if len(value_ranges) > 1 else []
        audit_timestamps = [row[0] for row in value_ranges[2].get('values', []) if row] if len(value_ranges) > 2 else []
    except Exception as e:
        logger.error(f"Failed to batch fetch state from Google Sheets: {e}")
        return
        
    existing_ids = set(details_ids) | set(audits_ids)
    
    # Clean up any headers that might have been fetched
    existing_ids.discard("Message ID")
    
    logger.info(f"Found {len(existing_ids)} previously processed emails in Sheets.")

    # Determine the last run timestamp from Audits sheet
    valid_timestamps = [ts for ts in audit_timestamps if ts != "Run Timestamp" and ts.strip()]
    
    # --- TESTING OVERRIDE ---
    # Forcing the search query to fetch emails from exactly 1 day ago (24 hours).
    search_after = int(datetime.now(timezone.utc).timestamp()) - (24 * 3600)
    logger.info(f"TESTING OVERRIDE: Fetching emails strictly from 1 day ago (Timestamp: {search_after})")
    
    # Original logic (Commented out for testing):
    # search_after = int(datetime.now(timezone.utc).timestamp()) - (7 * 24 * 3600) # Default: 7 days ago
    # if valid_timestamps:
    #     try:
    #         max_ts_str = max(valid_timestamps)
    #         parsed_date = datetime.fromisoformat(max_ts_str.replace(" ", "T"))
    #         search_after = int(parsed_date.timestamp()) - 3600
    #     except Exception as e:
    #         logger.warning(f"Could not parse last run timestamp, defaulting to 7 days ago: {e}")
    # ------------------------

    gmail_svc = gmail.get_service()

    logger.info(f"Fetching recent job-related emails...")
    
    dynamic_query = f"{GMAIL_JOB_SEARCH_QUERY} after:{search_after}"
    
    logger.info(f"Query: {dynamic_query}")

    results = gmail_svc.users().messages().list(
        userId='me',
        q=dynamic_query,
        maxResults=500
    ).execute()
    messages = results.get('messages', [])



    if not messages:
        logger.info("No emails found.")
        return

    logger.info(f"Found {len(messages)} candidate emails. Processing...")

    processed_count = 0
    skipped_count = 0

    for msg_meta in messages:
        msg_id = msg_meta['id']
        thread_id = msg_meta['threadId']

        if msg_id in existing_ids:
            logger.info(f"[{msg_id}] Already in Sheets. Skipping.")
            skipped_count += 1
            continue

        success = process_email(
            msg_id=msg_id,
            thread_id=thread_id,
            gmail_svc=gmail_svc,
            openrouter=openrouter,
            sheets=sheets,
            spreadsheet_id=spreadsheet_id,
            prompt_template=prompt_template,
        )

        if success:
            existing_ids.add(msg_id)  # Prevent re-processing within the same run
            processed_count += 1

    logger.info(f"Run complete. Processed: {processed_count}, Skipped (already in Sheets): {skipped_count}")


if __name__ == "__main__":
    main()
