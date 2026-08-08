import os
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class GoogleAPIClient:
    """Base class for handling Google API authentication and service building."""
    
    def __init__(self, service_name, service_version, scopes, credentials_file="credentials/credentials.json", token_file="credentials/token.json"):
        self.service_name = service_name
        self.service_version = service_version
        self.scopes = scopes
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.creds = None
        self.service = None

    def authenticate(self):
        if os.path.exists(self.token_file):
            self.creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)
        
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Failed to refresh token: {e}. Prompting for re-authentication.")
                    self._run_local_server_flow()
            else:
                self._run_local_server_flow()
            
            # Save the credentials for the next run
            with open(self.token_file, "w") as token:
                token.write(self.creds.to_json())

    def _run_local_server_flow(self):
        """Runs the local server flow to obtain new credentials."""
        if os.environ.get('CI'):
            raise RuntimeError('Cannot run interactive OAuth flow in CI — the refresh token is expired or invalid.')
        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(f"Credentials file '{self.credentials_file}' not found. "
                                    f"Please ensure it exists in your working directory.")
        flow = InstalledAppFlow.from_client_secrets_file(
            self.credentials_file, self.scopes
        )
        self.creds = flow.run_local_server(port=0)

    def get_service(self):
        """Returns the built API service object, authenticating if necessary."""
        if not self.service:
            if not self.creds or not self.creds.valid:
                self.authenticate()
            try:
                self.service = build(self.service_name, self.service_version, credentials=self.creds)
            except HttpError as error:
                logger.error(f"Failed to build {self.service_name} service: {error}")
                raise
        return self.service
