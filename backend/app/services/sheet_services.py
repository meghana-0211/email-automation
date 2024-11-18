import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import logging
from typing import List, Dict
from settings import settings

logger = logging.getLogger(__name__)

class SheetService:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    def __init__(self):
        self.creds = self.load_credentials()
    
    def load_credentials(self):
        try:
            # Use service account credentials directly
            from google.oauth2 import service_account
            
            credentials_path = r"C:\Users\Megha\OneDrive\Desktop\breakoutai\email-automation\backend\app\creds.json"
            
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(f"Credentials file not found at {credentials_path}")
            
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path, 
                scopes=self.SCOPES
            )
            
            return credentials
        
        except Exception as e:
            logger.error(f"Failed to load credentials: {str(e)}")
            raise

    def read_sheet(self, spreadsheet_id: str, range_name: str) -> List[Dict]:
        if not self.creds:
            raise ValueError("Google Sheets credentials not configured")
            
        try:
            service = build('sheets', 'v4', credentials=self.creds)
            sheet = service.spreadsheets()
            
            logger.info(f"Fetching data from spreadsheet {spreadsheet_id}, range {range_name}")
            result = sheet.values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                logger.warning("No data found in specified range")
                return []
            
            headers = values[0]
            data = []
            
            # Process rows into dictionaries
            for row_idx, row in enumerate(values[1:], start=2):
                row_dict = {}
                for col_idx, value in enumerate(row):
                    if col_idx < len(headers):
                        row_dict[headers[col_idx]] = value
                    else:
                        logger.warning(f"Row {row_idx} has more columns than headers")
                        break
                data.append(row_dict)
            
            logger.info(f"Successfully read {len(data)} rows from sheet")
            return data
            
        except Exception as e:
            logger.error(f"Failed to read Google Sheet: {str(e)}")
            raise

    def validate_spreadsheet_access(self, spreadsheet_id: str) -> bool:
        try:
            service = build('sheets', 'v4', credentials=self.creds)
            sheet = service.spreadsheets()
            sheet.get(spreadsheetId=spreadsheet_id).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to access spreadsheet {spreadsheet_id}: {str(e)}")
            return False