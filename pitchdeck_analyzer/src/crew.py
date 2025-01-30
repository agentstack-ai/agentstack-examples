from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from tools.fetch_emails import get_message_content
from tools.pdf_reader import upload_pdf, ask_question
from tools.write_to_docs import append_row
import os
import base64
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@CrewBase
class EmailFetcherCrew():
    """Crew for fetching emails, processing PDFs, and updating spreadsheets"""

    @task
    def process_emails(self) -> Task:
        """Process emails, download PDFs, extract data, and update spreadsheet."""
        self.get_emails()
        return Task(
            description="""
            1. Check the last 5 emails in the inbox
            2. Download PDF attachments
            3. Extract required information from PDFs
            4. Append extracted data to the spreadsheet
            """,
            expected_output="""
            A summary of processed emails, extracted data, and spreadsheet updates.
            """,
            agent=self.email_agent()
        )

    def get_emails(self):
        """Get the last 5 emails from Gmail and process attachments."""
        try:
            SCOPES = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/gmail.readonly'
            ]
            creds = None
            token_path = "src/token.json"
            
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        "src/tools/credentials.json", SCOPES)
                    creds = flow.run_local_server(port=0)
                with open(token_path, "w") as token:
                    token.write(creds.to_json())

            service = build("gmail", "v1", credentials=creds)
            results = service.users().messages().list(userId='me', maxResults=5).execute()
            messages = results.get('messages', [])

            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
                headers = msg['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'No Sender')
                
                print(f"\nEmail from: {sender}")
                print(f"Subject: {subject}")
                
                if 'parts' in msg['payload']:
                    for part in msg['payload']['parts']:
                        if part.get('filename', '').endswith('.pdf'):
                            attachment_id = part['body'].get('attachmentId')
                            if attachment_id:
                                file_path = self.download_attachment(service, message['id'], attachment_id)
                                if file_path:
                                    self.process_pdf(file_path)

        except Exception as e:
            print(f"Error accessing emails: {str(e)}")

    def download_attachment(self, service, message_id: str, attachment_id: str) -> str:
        """Download a PDF attachment from an email."""
        try:
            attachment = service.users().messages().attachments().get(
                userId='me', messageId=message_id, id=attachment_id).execute()
            
            file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
            
            # Save to current directory
            file_path = f'attachment_{message_id}.pdf'
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            print(f"Downloaded PDF: {file_path}")
            return file_path
            
        except Exception as e:
            print(f"Error downloading attachment: {str(e)}")
            return None

    def process_pdf(self, pdf_path: str):
        """Process the PDF to extract information and update the spreadsheet."""
        try:
            api_key = os.getenv("CHATPDF_API_KEY")
            if not api_key:
                print("ChatPDF API key not found. Please set the CHATPDF_API_KEY in your .env file.")
                return

            # Ensure the correct path is used
            pdf_path = os.path.abspath(pdf_path)
            print(f"Processing PDF: {pdf_path}")
            
            source_id = upload_pdf(api_key, pdf_path)
            if not source_id:
                print("Failed to upload PDF.")
                return

            print("PDF uploaded successfully. Extracting information...")
            
            questions = [
                "Who is the main team behind this company? Could be CTO, CEO, Co-Founder, Founder, Investor, etc. Definitely find upto 1 person. Only respond with name and title",
                "Who is the second main team behind this company? Could be CTO, CEO, Co-Founder, Founder, Investor, etc. Definitely find upto 1 person. Only respond with name and title",
                "Who is the third main team behind this company? Could be CTO, CEO, Co-Founder, Founder, Investor, etc. Definitely find upto 1 person. Only respond with name and title",
                "What is the company name?",
                "What is the main business idea or summary?",
                "What industry or sector is this company in?",
                "How much funding are they asking for (the ask amount)?",
                "Who are the competitors of this company and their details? What are other similar companies in the space and how are they doing? What are their names, revenue, valuation, etc?",
            ]

            results = {}
            for question in questions:
                print(f"\nAsking: {question}")
                answer = ask_question(api_key, source_id, question)
                if answer:
                    results[question] = answer
                    print(f"Answer: {answer}")
                else:
                    print(f"Failed to get answer for: {question}")
                    results[question] = ""

            print("\nUpdating spreadsheet with extracted information...")
            success = append_row(
                founder1=results.get("Who is the main team behind this company? Could be CTO, CEO, Co-Founder, Founder, Investor, etc. Definitely find upto 1 person. Only respond with name and title", ""),
                founder2=results.get("Who is the second main team behind this company? Could be CTO, CEO, Co-Founder, Founder, Investor, etc. Definitely find upto 1 person. Only respond with name and title", ""),
                founder3=results.get("Who is the third main team behind this company? Could be CTO, CEO, Co-Founder, Founder, Investor, etc. Definitely find upto 1 person. Only respond with name and title", ""),
                company_name=results.get("What is the company name?", ""),
                idea_summary=results.get("What is the main business idea or summary?", ""),
                industry=results.get("What industry or sector is this company in?", ""),
                ask=results.get("How much funding are they asking for (the ask amount)?", ""),
                competitors=results.get("Who are the competitors of this company?", ""),
            )

            if success:
                print("Spreadsheet updated successfully.")
            else:
                print("Failed to update spreadsheet.")

        except Exception as e:
            print(f"Error processing PDF: {str(e)}")

    @agent
    def email_agent(self) -> Agent:
        return Agent(
            name="EmailAgent",
            role="Email Processing Specialist",
            description="Expert at fetching emails, processing PDFs, and updating spreadsheets.",
            goal="Process recent emails, extract data from PDFs, and update spreadsheets.",
            backstory="An agent specialized in email processing and data extraction.",
            verbose=True
        )

    @crew
    def crew(self) -> Crew:
        """Creates the email processing crew"""
        return Crew(
            agents=[self.email_agent()],
            tasks=[self.process_emails()],
            process=Process.sequential,
            verbose=True
        )