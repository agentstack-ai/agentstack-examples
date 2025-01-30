import os.path
import base64
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify"
]

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Path to credentials relative to script location
CREDENTIALS_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "credentials.json")
TOKEN_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "token.json")

def get_message_content(service, msg_id):
    """Get the content of a specific message."""
    try:
        message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        
        # Get headers
        headers = message['payload']['headers']
        subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No Subject')
        from_email = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'No Sender')
        
        # Get message body
        if 'parts' in message['payload']:
            parts = message['payload']['parts']
            body = ''
            has_pdf = False
            
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif part['mimeType'] == 'application/pdf':
                    has_pdf = True
                # Check for PDF in attachments
                if 'filename' in part and part['filename'].lower().endswith('.pdf'):
                    has_pdf = True
        else:
            # Handle messages with no parts
            if 'body' in message['payload'] and 'data' in message['payload']['body']:
                body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
            else:
                body = 'No content'
            has_pdf = False
            
        return {
            'subject': subject,
            'from': from_email,
            'body': body,
            'has_pdf': has_pdf
        }
    except Exception as e:
        print(f"Error processing message {msg_id}: {str(e)}")
        return None

def main():
    """Fetch last 5 emails and their content."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        
        # Get list of messages
        results = service.users().messages().list(userId='me', maxResults=5).execute()
        messages = results.get('messages', [])

        if not messages:
            print("No messages found.")
            return

        print("\nFetching last 5 emails:\n")
        for message in messages:
            msg_data = get_message_content(service, message['id'])
            if msg_data:
                print(f"\nSubject: {msg_data['subject']}")
                print(f"From: {msg_data['from']}")
                print(f"Has PDF Attachment: {'Yes' if msg_data['has_pdf'] else 'No'}")
                print(f"Content Preview: {msg_data['body'][:200]}...")
                print("-" * 80)

    except HttpError as error:
        print(f"An error occurred: {error}")

if __name__ == "__main__":
    main()