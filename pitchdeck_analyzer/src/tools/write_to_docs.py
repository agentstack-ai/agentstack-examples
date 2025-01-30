from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path
from typing import Optional, List, Union

# If modifying these scopes, delete the token.json file.
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/gmail.readonly'
]

# Column structure matching the spreadsheet
COLUMNS = [
    'Founder Name 1',
    'Founder Name 2',
    'Founder Name 3',
    'Company Name',
    'Summary of Idea',
    'Industry/Sector',
    'Ask',
    'Valuation',
    'Previous Rounds',
    'Revenue/Traction',
    'Email'
]

def get_google_sheets_service():
    """Gets Google Sheets service with appropriate credentials."""
    creds = None
    # The file token.json stores the user's access and refresh tokens
    token_path = "src/token.json"
    
    if os.path.exists(token_path):
        try:
            os.remove(token_path)  # Remove existing token to force new authentication
            print("Removed existing token to refresh permissions.")
        except:
            pass
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'src/tools/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        print(f"Error building Google Sheets service: {str(e)}")
        return None

def append_row(
    founder1: Optional[str] = None,
    founder2: Optional[str] = None,
    founder3: Optional[str] = None,
    company_name: Optional[str] = None,
    idea_summary: Optional[str] = None,
    industry: Optional[str] = None,
    ask: Optional[str] = None,
    valuation: Optional[str] = None,
    previous_rounds: Optional[str] = None,
    revenue_traction: Optional[str] = None,
    email: Optional[str] = None
) -> bool:
    """
    Appends a row to the specified spreadsheet with the given values.
    Any None values will be added as empty cells.
    
    Args:
        founder1 (str, optional): Name of first founder
        founder2 (str, optional): Name of second founder
        founder3 (str, optional): Name of third founder
        company_name (str, optional): Name of the company
        idea_summary (str, optional): Summary of the business idea
        industry (str, optional): Industry/Sector
        ask (str, optional): Ask amount
        valuation (str, optional): Company valuation
        previous_rounds (str, optional): Previous funding rounds
        revenue_traction (str, optional): Revenue or traction metrics
        email (str, optional): Contact email
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        SPREADSHEET_ID = '1oOMFd-gijhkDmeYeVRSlvoQaQf5geolLV-N7MdIdYfY'
        RANGE_NAME = 'Sheet1!A:K'  # A to K for 11 columns
        
        service = get_google_sheets_service()
        if not service:
            print("Failed to get Google Sheets service")
            return False

        # Create row data with empty strings for None values
        row_data = [
            founder1 or '',
            founder2 or '',
            founder3 or '',
            company_name or '',
            idea_summary or '',
            industry or '',
            ask or '',
            valuation or '',
            previous_rounds or '',
            revenue_traction or '',
            email or ''
        ]

        # Prepare the data for appending
        values = [row_data]
        body = {
            'values': values
        }

        try:
            # Append the row
            result = service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range=RANGE_NAME,
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()

            updated_rows = result.get('updates', {}).get('updatedRows', 0)
            print(f"Row appended successfully: {updated_rows} rows added.")
            return True
        except Exception as e:
            print(f"Error appending to spreadsheet: {str(e)}")
            return False

    except Exception as e:
        print(f"Error in append_row: {str(e)}")
        return False

def main():
    # Example usage with some null values
    success = append_row(
        founder1="John Doe",
        founder2="Jane Smith",
        # founder3 is None/empty
        company_name="Tech Startup Inc.",
        idea_summary="AI-powered analytics platform",
        industry="Technology",
        ask="$2M",
        valuation="$10M",
        # previous_rounds is None/empty
        revenue_traction="$100K ARR",
        email="contact@techstartup.com"
    )
    
    if success:
        print("Row added successfully!")
    else:
        print("Failed to add row.")

if __name__ == '__main__':
    main()
