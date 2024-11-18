import pandas as pd
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path
import json
from typing import List, Dict
from settings import settings

class SheetService:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    
    def __init__(self):
        self.creds = None
        self.load_credentials()
    
    def load_credentials(self):
        if os.path.exists('creds.json'):
            with open('creds.json', 'r') as token:
                self.creds = Credentials.from_authorized_user_file('creds.json', self.SCOPES)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.GOOGLE_SHEETS_CREDENTIALS_PATH, self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open('creds.json', 'w') as token:
                token.write(self.creds.to_json())
    
    def read_sheet(self, spreadsheet_id: str, range_name: str) -> List[Dict]:
        service = build('sheets', 'v4', credentials=self.creds)
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])
        
        if not values:
            return []
            
        headers = values[0]
        data = []
        
        for row in values[1:]:
            row_dict = {}
            for i, value in enumerate(row):
                if i < len(headers):
                    row_dict[headers[i]] = value
            data.append(row_dict)
            
        return data
