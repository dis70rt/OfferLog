import logging
from googleapiclient.errors import HttpError
from src.google_auth import GoogleAPIClient

logger = logging.getLogger(__name__)

class GmailClient(GoogleAPIClient):
        
    DEFAULT_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    def __init__(self, credentials_file="credentials/credentials.json", token_file="credentials/gmail_token.json", scopes=None):
        """
        Initializes the GmailClient.

        Args:
            credentials_file (str): Path to the credentials.json file downloaded from Google Cloud Console.
            token_file (str): Path to store/load the user's access and refresh tokens.
            scopes (list): List of API scopes required. Defaults to read-only Gmail access.
        """
        scopes = scopes if scopes is not None else self.DEFAULT_SCOPES
        super().__init__(
            service_name="gmail",
            service_version="v1",
            scopes=scopes,
            credentials_file=credentials_file,
            token_file=token_file
        )

if __name__ == "__main__":
    # Example usage:
    logging.basicConfig(level=logging.INFO)
    
    # Initialize the client
    client = GmailClient()
    print("GmailClient initialized successfully.")
