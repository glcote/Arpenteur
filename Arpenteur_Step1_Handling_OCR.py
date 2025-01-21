# #############################################################
# # ------------- COUTE 1 Credit (0.08$) par PAGE ------------- #
# ##############################################################

import os
import logging
import requests
from dotenv import load_dotenv
import fitz  # PyMuPDF
from PIL import Image

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# API and global settings
api_key_handwriting_ocr = os.getenv("API_KEY_HANDWRITING_OCR")

# Folder paths
input_folder = "Document_du_Registre_Foncier"
output_folder = "Document_du_Registre_Foncier_PNG"
os.makedirs(input_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

###################################
# Utility Functions

def pdf_to_images(folder_input_path, file_name, output_folder):
    """
    Convert a PDF to images (one per page).
    Args:
        folder_input_path (str): Input folder containing the PDF file.
        file_name (str): Name of the PDF file to process.
        output_folder (str): Folder to save the converted images.
    Returns:
        list: A list of file paths to the generated images.
    """
    # Construct the full file path for the PDF
    pdf_file_path = os.path.join(folder_input_path, file_name)
    
    # Create an output directory for the images, named after the PDF (excluding its extension)
    output_directory = os.path.join(output_folder, os.path.splitext(file_name)[0])
    os.makedirs(output_directory, exist_ok=True)  # Ensure the directory exists

    image_paths = []  # List to store paths of generated images
    try:
        # Open the PDF using PyMuPDF (fitz)
        doc = fitz.open(pdf_file_path)
        
        # Iterate through each page in the PDF
        for page_num in range(len(doc)):
            try:
                # Load the current page
                page = doc.load_page(page_num)
                
                # Render the page to a pixmap
                pix = page.get_pixmap()
                
                # Convert the pixmap to an image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Define the output path for the image
                # image_path = os.path.join(output_directory, f"{file_name}_page_{page_num + 1}.png")
                image_path = os.path.join(output_directory, f"page_{page_num + 1}.png")
                
                # Save the image and append its path to the list
                img.save(image_path)
                image_paths.append(image_path)
                
                # Log successful save of the image
                logging.info(f"Saved image: {image_path}")
            except Exception as e:
                # Log errors during page processing
                logging.error(f"Error processing page {page_num + 1} in {file_name}: {e}")
        doc.close()  # Close the document after processing
    except Exception as e:
        # Log errors during PDF processing
        logging.error(f"Failed to process PDF {file_name}: {e}")

    return image_paths

def transcribe_file(file_dir):
    """
    Upload a file to the Handwriting OCR API and transcribe it.
    Args:
        file_dir (str): Path to the image file to transcribe.
    Returns:
        dict: The JSON response from the API containing the transcription result.
    """
    api_endpoint = "https://www.handwritingocr.com/api/v2/documents"

    # Prepare form data for the API request
    form_data = {
        "action": "transcribe",
        "delete_after": str(1209600),  # Time in seconds (14 days)
    }
    
    # Define request headers, including the API key
    headers = {
        "Authorization": f"Bearer {api_key_handwriting_ocr}",
        "Accept": "application/json",
    }

    try:
        # Open the image file in binary mode
        with open(file_dir, "rb") as file:
            # Extract the original file and page name
            file_name = file.name.split("/")[-2]
            page_name = file.name.split("/")[-1]
            file_page_name = f"{file_name}__{page_name}"

            # Create a files payload for the API request, using the modified file name
            files = {"file": (file_page_name, file)}

            # Send the POST request to the API
            response = requests.post(api_endpoint, headers=headers, data=form_data, files=files)
            
            # Raise an error if the request was unsuccessful
            response.raise_for_status()
            
            # Parse and return the JSON response
            result = response.json()
            logging.info(f"Transcribed file {file_dir} as {file_page_name}: {result}")
            return result
    except requests.RequestException as e:
        # Log errors during the API request
        logging.error(f"Failed to transcribe file {file_dir}: {e}")
        return {}

def process_pdfs(input_folder, output_folder):
    """
    Convert all PDF files in the input folder to images, transcribe them, and process the results.
    Move processed PDF files to a specific folder within the output folder.
    Args:
        input_folder (str): Path to the folder containing PDF files to process.
        output_folder (str): Path to the folder where processed images and PDFs will be saved.
    """
    # Iterate through all files in the input folder
    for file_name in os.listdir(input_folder):
        # Process only PDF files
        if file_name.endswith(".pdf"):
            logging.info(f"Processing file: {file_name}")

            # Convert the PDF to images
            image_paths = pdf_to_images(input_folder, file_name, output_folder)

            # Transcribe each generated image
            for image_path in image_paths:
                transcription_result = transcribe_file(image_path)
                
                if transcription_result:
                    # Log successful transcription
                    logging.info(f"Transcription result for {image_path}: {transcription_result}")
                else:
                    # Log if no transcription result was received
                    logging.warning(f"No transcription result for {image_path}.")

            # Move the processed PDF to the output folder
            pdf_output_folder = os.path.join(output_folder, os.path.splitext(file_name)[0])
            os.makedirs(pdf_output_folder, exist_ok=True)

            source_pdf_path = os.path.join(input_folder, file_name)
            destination_pdf_path = os.path.join(pdf_output_folder, file_name)

            try:
                os.rename(source_pdf_path, destination_pdf_path)
                logging.info(f"Moved PDF {file_name} to {destination_pdf_path}")
            except Exception as e:
                logging.error(f"Failed to move PDF {file_name}: {e}")

###################################
# Main Execution

if __name__ == "__main__":
    logging.info("Starting PDF to image conversion, transcription, and processing.")
    process_pdfs(input_folder, output_folder)
