import logging
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.google_auth import GoogleAPIClient

logger = logging.getLogger(__name__)

class SheetsClient(GoogleAPIClient):
    """A reusable client for interacting with the Google Sheets API."""
    
    # Scope for reading and writing to Google Sheets
    DEFAULT_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    def __init__(self, credentials_file="credentials/credentials.json", token_file="credentials/sheets_token.json", scopes=None):
        """
        Initializes the SheetsClient.

        Args:
            credentials_file (str): Path to the Google Cloud credentials.json file.
            token_file (str): Path to store/load the user's access and refresh tokens.
                              Defaults to 'sheets_token.json' to avoid scope conflicts with Gmail tokens.
            scopes (list): List of API scopes required.
        """
        scopes = scopes if scopes is not None else self.DEFAULT_SCOPES
        super().__init__(
            service_name="sheets",
            service_version="v4",
            scopes=scopes,
            credentials_file=credentials_file,
            token_file=token_file
        )

    def create_spreadsheet(self, title):
        """
        Creates a new Google Spreadsheet.

        Args:
            title (str): The name of the new spreadsheet.

        Returns:
            str: The spreadsheet ID, or None if creation failed.
        """
        try:
            service = self.get_service()
            spreadsheet = {
                'properties': {
                    'title': title
                }
            }
            spreadsheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
            spreadsheet_id = spreadsheet.get('spreadsheetId')
            logger.info(f"Created new spreadsheet with ID: {spreadsheet_id}")
            return spreadsheet_id
        except HttpError as error:
            logger.error(f"An error occurred creating spreadsheet: {error}")
            return None

    def add_worksheet(self, spreadsheet_id, title):
        """
        Adds a new worksheet (tab) to an existing spreadsheet.

        Args:
            spreadsheet_id (str): The ID of the spreadsheet.
            title (str): The name of the new worksheet.
        """
        try:
            service = self.get_service()
            body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': title
                        }
                    }
                }]
            }
            service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
            logger.info(f"Added worksheet '{title}' to spreadsheet '{spreadsheet_id}'")
        except HttpError as error:
            logger.error(f"An error occurred adding worksheet '{title}': {error}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type(HttpError),
        reraise=True
    )
    def _append_row_with_retry(self, spreadsheet_id, range_name, values):
        service = self.get_service()
        body = {
            'values': values
        }
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        logger.info(f"Appended {result.get('updates').get('updatedCells')} cells to {range_name}.")
        return result

    def append_row(self, spreadsheet_id, range_name, values):
        """
        Appends a row of data to a worksheet, with exponential backoff retries.
        """
        try:
            return self._append_row_with_retry(spreadsheet_id, range_name, values)
        except HttpError as error:
            logger.error(f"An error occurred appending row to {range_name} after retries: {error}")
            return None

    def get_column_values(self, spreadsheet_id, range_name):
        """
        Reads all values from a single column range.

        Args:
            spreadsheet_id (str): The ID of the spreadsheet.
            range_name (str): The A1 notation range, e.g., 'Details!I:I' for the Message ID column.

        Returns:
            list[str]: A flat list of cell values, or an empty list on error.
        """
        try:
            service = self.get_service()
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            # Flatten the list of lists into a single list of strings
            return [row[0] for row in result.get('values', []) if row]
        except HttpError as error:
            logger.error(f"An error occurred reading {range_name}: {error}")
            return []

if __name__ == "__main__":
    # Example Usage Snippet
    logging.basicConfig(level=logging.INFO)
    
    # client = SheetsClient()
    
    # Example 1: Create a new spreadsheet
    # spreadsheet_id = client.create_spreadsheet("OfferLog Data")
    
    # Example 2: Add the audits worksheet to it
    # if spreadsheet_id:
    #    client.add_worksheet(spreadsheet_id, "Audits")
    #
    #    # Example 3: Append data to the 'Details' worksheet (Sheet1 is default)
    #    client.append_row(spreadsheet_id, "Sheet1", [["Subject", "Sender", "Status"]])
    #    client.append_row(spreadsheet_id, "Audits", [["Run ID", "Tokens", "Cost", "Timestamp"]])
    pass
