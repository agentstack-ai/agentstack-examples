import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def upload_pdf(api_key: str, pdf_path: str):
    """Upload a PDF file and return the source ID."""
    if not os.path.exists(pdf_path):
        print(f"Error: File not found at {pdf_path}")
        return None

    try:
        with open(pdf_path, 'rb') as file:
            files = {'file': ('file.pdf', file, 'application/octet-stream')}
            
            response = requests.post(
                'https://api.chatpdf.com/v1/sources/add-file',
                headers={'x-api-key': api_key},
                files=files
            )

        if response.status_code == 200:
            data = response.json()
            source_id = data.get('sourceId')
            if source_id:
                print('Source ID:', source_id)
                return source_id
            else:
                print('Error: Missing "sourceId" in response')
                print('Response:', response.text)
        else:
            print('Status:', response.status_code)
            print('Error:', response.text)
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {str(e)}")
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")
    
    return None


def ask_question(api_key: str, source_id: str, question: str) -> str:
    """Ask a single question about the PDF."""
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json'
    }

    # Format the question to request concise answers
    formatted_question = f"Provide a direct, concise answer. If the information is not found in the document, respond with 'None'. {question}"

    data = {
        'sourceId': source_id,
        'messages': [{'role': 'user', 'content': formatted_question}]
    }

    try:
        response = requests.post(
            'https://api.chatpdf.com/v1/chats/message',
            headers=headers,
            json=data
        )

        if response.status_code == 200:
            json_response = response.json()
            answer = json_response.get('content', '').strip()
            # If the answer indicates no information was found, return None
            if any(phrase in answer.lower() for phrase in [
                "cannot find", "no information", "not mentioned", 
                "not specified", "not found", "not provided"
            ]):
                return "None"
            return answer
        else:
            print('Status:', response.status_code)
            print('Error:', response.text)
            return "None"
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {str(e)}")
        return "None"
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")
        return "None"


def main():
    # Use the ChatPDF API key from the environment
    API_KEY = os.getenv("CHATPDF_API_KEY")
    if not API_KEY:
        print("ChatPDF API key not found. Please set the CHATPDF_API_KEY in your .env file.")
        return
    
    pdf_path = os.path.abspath("src/your_pdf.pdf")
    
    source_id = upload_pdf(API_KEY, pdf_path)
    if not source_id:
        print("Failed to upload PDF. Exiting.")
        return

    questions = ["What is Elon Musk most known for?", "What are the key achievements of Elon Musk?"]
    for question in questions:
        result = ask_question(API_KEY, source_id, question)
        if result:
            print('Result:', result)
        else:
            print(f"Failed to get a response from ChatPDF for the question: {question}")


if __name__ == "__main__":
    main()
