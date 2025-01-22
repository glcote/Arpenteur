import os
import re
import logging
import requests
from dotenv import load_dotenv
from openai import OpenAI

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
        params = {"per_page": per_page, "page": page}
        headers = {
            "Authorization": f"Bearer {api_key_handwriting_ocr}",
            "Accept": "application/json",
        }
        response = requests.get(api_endpoint, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error fetching document list: {e}")
        return []

def clean_file(file_path):
    """
    Clean the content of a file by applying regex-based replacements.
    
    Args:
        file_path (str): Path to the file to be cleaned.
    """
    try:
        file_name = os.path.basename(file_path)
        if re.match(r"page_\d+", file_name):
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            updated_content = re.sub(r"=== \*\*Page: 1 of 1\*\*", "", content)
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(updated_content)
            logging.info(f"Cleaned file: {file_name}")
    except Exception as e:
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
        url = f"{api_endpoint}/{document_id}.{output_format}"
        headers = {
            "Authorization": f"Bearer {api_key_handwriting_ocr}",
            "Accept": "application/json",
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        file_name = re.sub(r".+__", "", original_file_name)
        folder_name = re.sub(r"__.+", "", original_file_name)
        folder_path = os.path.join(output_folder, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, f"{file_name}.{output_format}")
        with open(file_path, "wb") as file:
            file.write(response.content)
        logging.info(f"Downloaded and saved document: {file_path}")
        clean_file(file_path)
    except requests.RequestException as e:
        logging.error(f"Failed to download document {document_id}: {e}")

def combine_page_files(output_folder):
    """
    Combine all page_*.txt files in each subfolder into a single _Combine.txt file.
    Cleans each page_x.txt file using the clean_file function before combining.

    Args:
        output_folder (str): Path to the main output folder containing subfolders.
    """
    for folder_name in os.listdir(output_folder):
        folder_path = os.path.join(output_folder, folder_name)
        if os.path.isdir(folder_path):  # Vérifier si c'est un dossier
            output_file_path = os.path.join(folder_path, f"{folder_name}_Combine.txt")
            with open(output_file_path, 'w', encoding='utf-8') as output_file:
                for file_name in sorted(os.listdir(folder_path)):
                    if file_name.startswith("page_") and file_name.endswith(".txt"):
                        file_path = os.path.join(folder_path, file_name)
                        try:
                            # Clean the page_x.txt file
                            clean_file(file_path)
                            # Read the cleaned file and append its content
                            with open(file_path, "r", encoding="utf-8") as input_file:
                                output_file.write(input_file.read())
                                output_file.write("\n")  # Ajouter une ligne vide entre les pages
                        except Exception as e:
                            logging.error(f"Error processing file {file_path}: {e}")
            logging.info(f"Created combined file: {output_file_path}")

###################################
# Main Execution

if __name__ == "__main__":
    logging.info("Starting PDF to image conversion and processing.")
    documents = list_documents()
    for document in documents:
        document_id = document.get("document_id")
        original_file_name = document.get("original_file_name", "document")
        if document_id:
            download_document(document_id, original_file_name)
    combine_page_files(output_folder)
    logging.info("All page files have been combined and saved.")
