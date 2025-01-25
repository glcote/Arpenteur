import os
import re
import csv
import logging
import requests
import fitz
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# API and global settings
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
api_key_ocr_space = os.getenv("OCR_SPACE_API_KEY")
api_key_handwriting_ocr = os.getenv("API_KEY_HANDWRITING_OCR")
gpt_model = "gpt-4o-mini"

# Folder paths
input_folder = "staging"
output_folder = "data_lake"
os.makedirs(input_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

# Convert a PDF to images (one per page).
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

# Upload a file to the Handwriting OCR API and transcribe it.
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

# Convert all PDF files in the input folder to images, transcribe them using Handwriting OCR API.
def process_pdfs(input_folder, output_folder):
    """
    Convert all PDF files in the input folder to images, transcribe them using Handwriting OCR API.
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

# Retrieve a list of .txt documents from the Handwriting OCR API.
def list_documents(per_page=50, page=1):
    """
    Retrieve a list of .txt documents from the Handwriting OCR API.
    
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

# Clean the content of a file by applying regex-based replacements.
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

# Download and save .txt documents from Handwriting OCR API, then clean the files.
def download_document(document_id, original_file_name, output_format="txt"):
    """
    Download and save .txt documents from Handwriting OCR API, then clean the files.
    
    Args:
        document_id (str): The ID of the document to be downloaded.
        original_file_name (str): The name of the original file for naming purposes.
        output_format (str): The format in which to download the document (default is "txt").
    """
    try:
        # API endpoint and URL for downloading the document
        api_endpoint = "https://www.handwritingocr.com/api/v2/documents"
        url = f"{api_endpoint}/{document_id}.{output_format}"

        # API request headers, including the authorization token
        headers = {
            "Authorization": f"Bearer {api_key_handwriting_ocr}",
            "Accept": "application/json",
        }

        # Send a GET request to the API to download the document
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error if the request fails

        # Extract the file name and folder name from the original file name
        file_name = re.sub(r".+__", "", original_file_name)  # Remove everything before "__"
        folder_name = re.sub(r"__.+", "", original_file_name)  # Remove everything after "__"

        # Create a folder path for saving the document
        folder_path = os.path.join(output_folder, folder_name)
        os.makedirs(folder_path, exist_ok=True)  # Create the folder if it doesn't exist

        # Define the full file path with the specified output format
        file_path = os.path.join(folder_path, f"{file_name}.{output_format}")

        # Write the downloaded content to the file
        with open(file_path, "wb") as file:
            file.write(response.content)

        # Log success message
        logging.info(f"Downloaded and saved document: {file_path}")

        # Clean the downloaded file (assumes `clean_file` is defined elsewhere)
        clean_file(file_path)
    except requests.RequestException as e:
        # Log an error if the download fails
        logging.error(f"Failed to download document {document_id}: {e}")

# Combine all page_*.txt files in each subfolder into a single _Combine.txt file.
def combine_page_files(output_folder):
    """
    Combine all page_*.txt files in each subfolder into a single _Combine.txt file.
    Cleans each page_x.txt file using the clean_file function before combining.

    Args:
        output_folder (str): Path to the main output folder containing subfolders.
    """
    # Iterate through each folder in the output folder
    for folder_name in os.listdir(output_folder):
        folder_path = os.path.join(output_folder, folder_name)

        # Check if the current item is a folder
        if os.path.isdir(folder_path):  
            # Define the path for the combined output file
            output_file_path = os.path.join(folder_path, f"{folder_name}_Combine.txt")

            # Open the combined output file in write mode
            with open(output_file_path, 'w', encoding='utf-8') as output_file:
                # Sort and iterate through the files in the folder
                for file_name in sorted(os.listdir(folder_path)):
                    # Process only files that match the "page_*.txt" pattern
                    if file_name.startswith("page_") and file_name.endswith(".txt"):
                        file_path = os.path.join(folder_path, file_name)
                        try:
                            # Clean the page_x.txt file using the clean_file function
                            clean_file(file_path)
                            
                            # Read the cleaned file and append its content to the combined file
                            with open(file_path, "r", encoding="utf-8") as input_file:
                                output_file.write(input_file.read())
                                # Add a blank line between the contents of different pages
                                output_file.write("\n")
                        except Exception as e:
                            # Log an error if there's an issue with processing the file
                            logging.error(f"Error processing file {file_path}: {e}")
            
            # Log a message indicating the combined file was created successfully
            logging.info(f"Created combined file: {output_file_path}")

# Reads a text file, interacts with GPT to generate a response, and saves the result directly into a CSV file.
def gpt_txt_file(txt_file_path, sys_prompt, user_prompt, output_csv_file_name="txt"):
    """
    Reads a text file, interacts with GPT to generate a response, and saves the result directly into a CSV file.

    Args:
        txt_file_path (str): Path to the text file.
        sys_prompt (str): System prompt to guide the model.
        user_prompt (str): User prompt to specify the response needed.

    Returns:
        str: Content generated by GPT.
    """
    # Read the content of the text file
    try:
        with open(txt_file_path, 'r', encoding='utf-8') as file:
            txt_file_content = file.read()
    except FileNotFoundError:
        # Log an error if the file is not found
        logging.error("Le fichier spécifié est introuvable.")
        return "Le fichier spécifié est introuvable."
    except Exception as e:
        # Log any other exceptions that occur
        logging.error(f"Une erreur s'est produite : {str(e)}")
        return f"Une erreur s'est produite : {str(e)}"

    # Define a default question prompt and assistant's answer for context
    question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
    assistant_answer = f"Oui, voici le contenu du document : {txt_file_content}"

    # Initialize the message history for the GPT conversation
    message_history = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": question_prompt},
        {"role": "assistant", "content": assistant_answer},
        {"role": "user", "content": user_prompt}
    ]

    # Call the GPT completion API
    try:
        completion = client.chat.completions.create(
            model=gpt_model,
            messages=message_history,
        )

        # Extract data from the API response
        gen_answ_content = completion.choices[0].message.content
        gen_answ_data = {
            "txt_file_path": txt_file_path,
            "sys_prompt": sys_prompt,
            "question_prompt": question_prompt,
            # "assistant_answer": assistant_answer,
            "user_prompt": user_prompt,
            "gen_answ_id": completion.id,
            "gen_answ_content": gen_answ_content,
            "gen_answ_role": completion.choices[0].message.role,
            "gen_answ_created": completion.created,
            "gen_answ_model": completion.model,
            "gen_answ_completion_tokens": completion.usage.completion_tokens,
            "gen_answ_prompt_tokens": completion.usage.prompt_tokens,
            "gen_answ_total_tokens": completion.usage.total_tokens
        }

        # Save the data into a CSV file
        try:
            with open(output_csv_file_name, mode='w', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(gen_answ_data.keys())  # En-têtes
                writer.writerow(gen_answ_data.values())  # Valeurs

            logging.info(f"Données enregistrées avec succès dans {output_csv_file_name}.")
        except Exception as e:
            logging.error(f"Une erreur s'est produite lors de l'enregistrement du fichier CSV : {str(e)}")

        return gen_answ_content

    except Exception as e:
        logging.error(f"Une erreur s'est produite lors de l'appel à l'API : {str(e)}")
        return f"Une erreur s'est produite lors de l'appel à l'API : {str(e)}"

# Manages a list of user prompts and generates responses for each.
def gpt_batch_txt_file(txt_file_path, sys_prompt, user_prompts, output_csv_file):
    """
    Manages a list of user prompts and generates responses for each.

    Args:
        txt_file_path (str): Path to the text file.
        sys_prompt (str): System prompt to guide the model.
        user_prompts (list): List of user prompts.
        output_csv_file (str): Path to the CSV file where results will be saved.
    
    Returns:
        list: A list of contents generated by GPT for each prompt.
    """
    all_responses = []

    # Create the CSV file with headers in advance
    try:
        with open(output_csv_file, mode='w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            # Define the headers for the CSV file
            headers = [
                "txt_file_path", "sys_prompt", "question_prompt",
                "assistant_answer", "user_prompt", "gen_answ_id",
                "gen_answ_content", "gen_answ_role", "gen_answ_created",
                "gen_answ_model", "gen_answ_completion_tokens",
                "gen_answ_prompt_tokens", "gen_answ_total_tokens"
            ]
            writer.writerow(headers)  # Write the headers to the CSV file
    except Exception as e:
        # Log an error if the CSV file creation fails
        logging.error(f"Error while creating the CSV file: {str(e)}")
        return []

    # Process each user prompt
    for user_prompt in user_prompts:
        # Call `txt_file_to_gpt` for each user prompt
        response = txt_file_to_gpt(txt_file_path, sys_prompt, user_prompt, output_csv_file)
        all_responses.append(response)  # Store the response in the list

        # Add the data for this specific prompt to the CSV file
        try:
            with open(output_csv_file, mode='a', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)

                # Write the row for the current prompt
                writer.writerow([
                    txt_file_path,  # Path to the input text file
                    # sys_prompt,  # System prompt guiding the GPT model
                    # "I sent you a document. Did you receive it?",  # Default question prompt
                    # f"Yes, here is the content of the document: {open(txt_file_path, 'r', encoding='utf-8').read()}",
                    user_prompt,  # User-specific prompt
                    # "N/A",  # Placeholder for generation ID (if not available)
                    response,  # Generated response content
                    # "N/A",  # Placeholder for response role (if not available)
                    # "N/A",  # Placeholder for creation timestamp (if not available)
                    # gpt_model,  # Model used for generating the response
                    # "N/A",  # Placeholder for completion tokens (if not available)
                    # "N/A",  # Placeholder for prompt tokens (if not available)
                    # "N/A"   # Placeholder for total tokens (if not available)
                ])

        except Exception as e:
            # Log an error if writing to the CSV fails
            logging.error(f"Erreur lors de l'enregistrement des données dans le CSV : {str(e)}")

    return all_responses  # Return all generated responses as a list

# Retrieves a list of text files with '_Combine' in their filenames from all subfolders.
def get_combine_txt_files_in_subfolders(folder):
    """
    Retrieves a list of text files with '_Combine' in their filenames from all subfolders.

    Args:
        folder (str): The root folder to search for text files.

    Returns:
        list: A list of full file paths for text files meeting the criteria.
    """
    txt_files = []  # Initialize an empty list to store file paths

    # Walk through the folder and its subfolders
    for root, _, files in os.walk(folder):
        for file in files:
            # Check if the file is a text file and contains '_Combine' in its name
            if file.endswith('.txt') and '_Combine' in file:
                # Get the full path of the file
                full_path = os.path.join(root, file)
                txt_files.append(full_path)  # Add the file path to the list

    return txt_files  # Return the list of matching file paths

# Function to retrieve all PNG files in the same folder as the given text file
def get_png_files_in_same_folder(txt_file):
    """
    Retrieves all PNG files in the same folder as the specified text file, 
    and sorts them by the page number extracted from their filenames.

    Args:
        txt_file (str): Path to the text file.

    Returns:
        list: A sorted list of PNG file paths based on page numbers.
    """
    # Get the folder path containing the text file
    folder = os.path.dirname(txt_file)
    
    # Retrieve all PNG files in the folder
    png_files = [os.path.join(folder, file) for file in os.listdir(folder) if file.endswith('.png')]
    
    # Define a helper function to extract the page number from the file name
    def extract_page_number(filename):
        match = re.search(r'page_(\d+)\.png', filename)  # Look for "page_{number}.png"
        return int(match.group(1)) if match else float('inf')  # Return a high value if no number is found

    # Sort PNG files based on the extracted page number
    png_files.sort(key=lambda x: extract_page_number(os.path.basename(x)))
    
    return png_files  # Return the sorted list of PNG file paths
