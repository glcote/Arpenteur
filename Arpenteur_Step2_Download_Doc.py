import os
import re
import logging
import requests
from dotenv import load_dotenv
from openai import OpenAI
# import fitz  # PyMuPDF
# from PIL import Image

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# API and global settings
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
api_key_ocr_space = os.getenv("OCR_SPACE_API_KEY")
api_key_handwriting_ocr = os.getenv("API_KEY_HANDWRITING_OCR")
# api_endpoint = "https://www.handwritingocr.com/api/v2/documents"
gpt_model = "gpt-4o-mini"

# Folder paths
input_folder = "Document_du_Registre_Foncier"
output_folder = "Document_du_Registre_Foncier_PNG"
os.makedirs(input_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

###################################
# Utility Functions

def list_documents(per_page=50, page=1):
    """
    Retrieve a paginated list of documents from the Handwriting OCR API.
    
    Args:
        per_page (int): The number of documents to retrieve per page. Default is 50.
        page (int): The page number to retrieve. Default is 1.

    Returns:
        list: A list of documents retrieved from the API, or an empty list if an error occurs.
    """
    try:
        api_endpoint = "https://www.handwritingocr.com/api/v2/documents"
        # Define the query parameters for the API request
        params = {"per_page": per_page, "page": page}
        
        # Headers for API requests
        headers = {
            "Authorization": f"Bearer {api_key_handwriting_ocr}",
            "Accept": "application/json",
        }

        # Make a GET request to the API with the provided parameters
        response = requests.get(api_endpoint, headers=headers, params=params)
        
        # Raise an HTTPError if the response contains an error status code
        response.raise_for_status()
        
        # Parse and return the JSON response from the API
        return response.json()
    except requests.RequestException as e:
        # Log an error message if the API request fails
        logging.error(f"Error fetching document list: {e}")
        # Return an empty list to indicate failure
        return []

def clean_file(file_path):
    """
    Clean the content of a file by applying regex-based replacements.
    
    Args:
        file_path (str): Path to the file to be cleaned.
    """
    try:
        # Extract the file name from the full file path
        file_name = os.path.basename(file_path)
        
        # Check if the file name matches the regex pattern (e.g., "page_1", "page_2", etc.)
        if re.match(r"page_\d+", file_name):
            # Open the file in read mode and read its content
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            
            # Apply regex substitution to remove specific unwanted text
            updated_content = re.sub(r"=== \*\*Page: 1 of 1\*\*", "", content)
            
            # Open the file in write mode and save the cleaned content
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(updated_content)
            
            # Log a success message indicating the file has been cleaned
            logging.info(f"Cleaned file: {file_name}")
    except Exception as e:
        # Log an error message if any exception occurs during the cleaning process
        logging.error(f"Error cleaning file {file_path}: {e}")

def download_document(document_id, original_file_name, output_format="txt"):
    """
    Download and save a processed document, then clean the files in the folder.
    
    Args:
        document_id (str): The ID of the document to be downloaded.
        original_file_name (str): The name of the original file for naming purposes.
        output_format (str): The format in which to download the document (default is "txt").
    """
    try:
        api_endpoint = "https://www.handwritingocr.com/api/v2/documents"
        # Construct the API URL to download the document
        url = f"{api_endpoint}/{document_id}.{output_format}"
        
        # Headers for API requests
        headers = {
            "Authorization": f"Bearer {api_key_handwriting_ocr}",
            "Accept": "application/json",
        }

        # Make a GET request to download the document
        response = requests.get(url, headers=headers)
        
        # Raise an HTTPError if the response contains an error status code
        response.raise_for_status()
        
        print(f"original_file_name: {original_file_name}")

        # Remove unnecessary parts of the file name (e.g., page numbers and PDF extension)
        file_name = re.sub(r".+__", "", original_file_name)
        folder_name = re.sub(r"__.+", "", original_file_name)
        
        # Create a folder named after the base file name in the output folder
        folder_path = os.path.join(output_folder, folder_name)
        os.makedirs(folder_path, exist_ok=True)  # Ensure the folder exists
        
        # Construct the path to save the downloaded file
        file_path = os.path.join(folder_path, f"{file_name}.{output_format}")
        
        # Save the downloaded content as a file
        with open(file_path, "wb") as file:
            file.write(response.content)
        
        # Log a success message indicating the document has been saved
        logging.info(f"Downloaded and saved document: {file_path}")
        
        # Clean the content of the downloaded file
        clean_file(file_path)
    except requests.RequestException as e:
        # Log an error message if the document download fails
        logging.error(f"Failed to download document {document_id}: {e}")

###################################
# Main Execution

if __name__ == "__main__":
    logging.info("Starting PDF to image conversion and processing.")
    # process_pdfs(input_folder, output_folder)

    documents = list_documents()  # Call the function to retrieve documents

    # Process each document in the list
    for document in documents:
        # print(document)
        document_id = document.get("document_id")
        original_file_name = document.get("original_file_name", "document")
        
        # Ensure the document ID exists before proceeding
        if document_id:
            download_document(document_id, original_file_name)
