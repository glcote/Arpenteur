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

# Lit le contenu d'un fichier texte et retourne une réponse formatée.
def read_file(output_file_path_txt):
    """
    Lit le contenu d'un fichier texte et retourne une réponse formatée.
    
    :param output_file_path_txt: Chemin vers le fichier texte.
    :return: Chaîne contenant le contenu du document ou un message d'erreur.
    """
    try:
        with open(output_file_path_txt, "r", encoding="utf-8") as file:
            content = file.read()
        return content
    except Exception as e:
        return f"Erreur lors de la lecture du document : {e}"

# Convert a PDF to images (one per page).
def pdf_to_images(input_folder, file_name, output_folder):
    """
    Convert a PDF to images (one per page).
    Args:
        input_folder (str): Input folder containing the PDF file.
        file_name (str): Name of the PDF file to process.
        output_folder (str): Folder to save the converted images.
    Returns:
        list: A list of file paths to the generated images.
    """
    # Construct the full file path for the PDF
    pdf_file_path = os.path.join(input_folder, file_name)
    
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
                image_path = os.path.join(output_directory, f"page_{page_num + 1}.png")
                
                # Save the image and append its path to the list
                img.save(image_path)
                image_paths.append(image_path)
                
                # Log successful save of the image
                logging.info(f"Image saved : {image_path}")
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

# Convert all PDF files in the input folder to images, transcribe them using Handwriting OCR API.process_pdfs
def pdf_to_ocr(input_folder, output_folder):
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

# Clean the content of a file by applying regex-based replacements.clean_file
def ocr_clean_txt_file(file_path):
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


# Retrieve a list of .txt documents from the Handwriting OCR API.list_documents
def ocr_list_txt_file(per_page=50, page=1):
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

# Download and save .txt documents from Handwriting OCR API, then clean the files.download_document
def ocr_download_txt_file(document_id, original_file_name, output_format="txt"):
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
        file_name = re.sub(r".+__|\.png", "", original_file_name)  # Remove everything before "__"
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

        # Clean the downloaded file (assumes `ocr_clean_txt_file` is defined elsewhere)
        ocr_clean_txt_file(file_path)
    except requests.RequestException as e:
        # Log an error if the download fails
        logging.error(f"Failed to download document {document_id}: {e}")

# Combine all page_*.txt files in each subfolder into a single _Combine.txt file.combine_page_files
def ocr_combine_txt_file(output_folder):
    """
    Combine all page_*.txt files in each subfolder into a single _Combine.txt file.
    Cleans each page_x.txt file using the ocr_clean_txt_file function before combining.

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
                            # Clean the page_x.txt file using the ocr_clean_txt_file function
                            ocr_clean_txt_file(file_path)
                            
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

# Retrieve a list of .txt then Download and save .txt documents
def ocr_list_download_combine_txt_file(per_page=50, page=1, output_format="txt"):
    """
    List and download .txt documents from the Handwriting OCR API.

    Args:
        per_page (int): The number of documents to retrieve per page. Default is 50.
        page (int): The page number to retrieve. Default is 1.
        output_format (str): The format in which to download the documents. Default is "txt".
    """
    try:
        # Retrieve the list of documents
        documents = ocr_list_txt_file(per_page=per_page, page=page)
        
        if not documents:
            logging.warning("Aucun document trouvé ou erreur lors de la récupération des documents.")
            return

        # Iterate through the list of documents and download each one
        for document in documents:
            document_id = document.get("document_id")
            original_file_name = document.get("original_file_name", "document")

            if document_id:
                ocr_download_txt_file(document_id, original_file_name, output_format)
                ocr_combine_txt_file(output_folder)
            else:
                logging.warning(f"Document sans ID trouvé : {original_file_name}")
    except Exception as e:
        logging.error(f"Erreur lors de la liste et du téléchargement des documents : {e}")



def save_uploaded_file(uploaded_file, input_file_path, output_file_path_pdf):
    """
    Save the uploaded file to the specified input path and make a copy at the output path.

    Args:
        uploaded_file: The uploaded file object (e.g., from Streamlit's file_uploader).
        input_file_path (str): The file path where the original file should be saved.
        output_file_path_pdf (str): The file path where a copy of the file should be saved.
    """
    # Sauvegarder le fichier téléchargé dans le dossier spécifié
    with open(input_file_path, "wb") as input_file:
        input_file.write(uploaded_file.getbuffer())
    logging.info(f"File saved : {input_file_path}")

    # Sauvegarder une copie dans le dossier de sortie
    os.makedirs(os.path.dirname(output_file_path_pdf), exist_ok=True)  # Crée le sous-dossier si nécessaire
    with open(output_file_path_pdf, "wb") as output_file:
        output_file.write(uploaded_file.getbuffer())
    logging.info(f"File saved : {output_file_path_pdf}")


def read_text_file(file_path):
    """
    Reads the content of a text file.

    Args:
        file_path (str): The path to the text file to read.

    Returns:
        str: The content of the file if successful, or None if an error occurs.
    """
    try:
        # Open the file in read mode with UTF-8 encoding
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        # Log an error if the file is not found
        logging.error("Le fichier spécifié est introuvable.")
        return None
    except Exception as e:
        # Log any other errors that occur during file reading
        logging.error(f"Une erreur s'est produite : {str(e)}")
        return None

def save_to_txt(data, output_file_name, operation="insert"):
    """
    Saves, updates, or deletes lines in a text file.

    Args:
        data: 
            - For "insert" and "delete": a string representing the line to insert or delete.
            - For "update": a dictionary with two keys:
                "old": the exact line content to search for,
                "new": the new line content to replace the matching line.
        output_file_name (str): The name of the text file.
        operation (str): The operation to perform - "insert", "update", or "delete".

    Returns:
        None
    """
    file_exists = os.path.isfile(output_file_name)

    try:
        if operation == "insert":
            mode = 'a' if file_exists else 'w'
            with open(output_file_name, mode=mode, encoding='utf-8') as file:
                if isinstance(data, list):
                    # Write each item in the list on a new line
                    for item in data:
                        file.write(item.rstrip("\n") + "\n")
                else:
                    file.write(data.rstrip("\n") + "\n")
            logging.info(f"Line inserted into {output_file_name} successfully.")
        # if operation == "insert":
        #     # Append the new line if the file exists; otherwise, create a new file.
        #     mode = 'a' if file_exists else 'w'
        #     with open(output_file_name, mode=mode, encoding='utf-8') as file:
        #         file.write(data.rstrip("\n") + "\n")
        #     logging.info(f"Line inserted into {output_file_name} successfully.")

        elif operation == "update":
            if not file_exists:
                logging.error("Cannot update as the file does not exist.")
                return

            # For update, expect data to be a dictionary with "old" and "new" keys.
            if not isinstance(data, dict) or "old" not in data or "new" not in data:
                logging.error("For update operation, data must be a dictionary with keys 'old' and 'new'.")
                return

            old_line = data["old"].rstrip("\n")
            new_line = data["new"].rstrip("\n")

            # Read all lines from the file.
            with open(output_file_name, mode='r', encoding='utf-8') as file:
                lines = file.readlines()

            updated = False
            new_lines = []
            for line in lines:
                # Compare the stripped line (without newline) to find a match.
                if line.rstrip("\n") == old_line:
                    new_lines.append(new_line + "\n")
                    updated = True
                else:
                    new_lines.append(line)

            if not updated:
                logging.warning("No matching line found to update.")

            # Write back the updated lines.
            with open(output_file_name, mode='w', encoding='utf-8') as file:
                file.writelines(new_lines)
            logging.info(f"Line updated in {output_file_name} successfully.")

        elif operation == "delete":
            if not file_exists:
                logging.error("Cannot delete as the file does not exist.")
                return

            # For delete, data should be the exact line (as a string) to remove.
            target_line = data.rstrip("\n")

            with open(output_file_name, mode='r', encoding='utf-8') as file:
                lines = file.readlines()

            deleted = False
            new_lines = []
            for line in lines:
                if line.rstrip("\n") == target_line:
                    deleted = True
                    # Skip writing this line to effectively delete it.
                else:
                    new_lines.append(line)

            if not deleted:
                logging.warning("No matching line found to delete.")

            with open(output_file_name, mode='w', encoding='utf-8') as file:
                file.writelines(new_lines)
            logging.info(f"Line deleted from {output_file_name} successfully.")

        else:
            logging.error(f"Invalid operation: {operation}. Must be 'insert', 'update', or 'delete'.")

    except Exception as e:
        logging.error(f"An error occurred during the {operation} operation: {str(e)}")

def save_to_csv(dict_data, output_file_name, operation="insert"):
    """
    Saves, updates, or deletes rows in a CSV file.

    Args:
        dict_data (dict): A dictionary containing the dict_data to save (keys as headers, values as rows).
        output_file_name (str): The name of the CSV file to save the dict_data.
        operation (str): The operation to perform - "insert", "update", or "delete/insert".

    Returns:
        None
    """
    # Check if the file exists
    file_exists = os.path.isfile(output_file_name)
    
    try:
        if operation == "insert":
            # Append new row if the file exists, otherwise write headers and row
            with open(output_file_name, mode='a' if file_exists else 'w', encoding='utf-8', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=dict_data.keys())
                
                # Write headers if the file is new
                if not file_exists:
                    writer.writeheader()
                
                # Write the new row
                writer.writerow(dict_data)
            logging.info(f"Row inserted into {output_file_name} successfully.")

        elif operation == "update":
            # Read all rows, update the matching row, and rewrite the file
            if not file_exists:
                logging.error("Cannot update as the file does not exist.")
                return
            
            rows = []
            updated = False  # Track if any row was updated
            
            with open(output_file_name, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # Match all fields for the update condition
                    if (
                        row["sys_prompt"] == dict_data["sys_prompt"] and
                        row["question_prompt"] == dict_data["question_prompt"] and
                        row["assistant_answer"] == dict_data["assistant_answer"] and
                        row["user_prompt"] == dict_data["user_prompt"]
                    ):
                        rows.append(dict_data)  # Update with new dict_data
                        updated = True
                    else:
                        rows.append(row)
            
            # If no row was updated, log a warning
            if not updated:
                logging.warning("No matching row found to update.")
            
            # Write back updated rows
            with open(output_file_name, mode='w', encoding='utf-8', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=dict_data.keys())
                writer.writeheader()
                writer.writerows(rows)
            logging.info(f"Row updated in {output_file_name} successfully.")

        elif operation == "delete":
            # Read all rows, exclude the matching row, and rewrite the file
            if not file_exists:
                logging.error("Cannot delete as the file does not exist.")
                return
            
            rows = []
            deleted = False  # Track if any row was deleted
            
            with open(output_file_name, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # Match all fields for the delete condition
                    if (
                        row["sys_prompt"] == dict_data["sys_prompt"] and
                        row["question_prompt"] == dict_data["question_prompt"] and
                        row["assistant_answer"] == dict_data["assistant_answer"] and
                        row["user_prompt"] == dict_data["user_prompt"]
                    ):
                        deleted = True  # Skip adding this row (deleting it)
                    else:
                        rows.append(row)
            
            # If no row was deleted, log a warning
            if not deleted:
                logging.warning("No matching row found to delete.")
            
            # Write back remaining rows
            with open(output_file_name, mode='w', encoding='utf-8', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=dict_data.keys())
                writer.writeheader()
                writer.writerows(rows)
            logging.info(f"Row deleted from {output_file_name} successfully.")
        else:
            logging.error(f"Invalid operation: {operation}. Must be 'insert', 'update', or 'delete'.")
    except Exception as e:
        logging.error(f"An error occurred during the {operation} operation: {str(e)}")

# Reads a text file, interacts with GPT to generate a response, and saves the result into a CSV file. 
def gpt_prompt(sys_prompt=None, question_prompt=None, assistant_answer=None, user_prompt=None):
    """
    Constructs a message history for a GPT conversation and sends it to the GPT model.

    Args:
        sys_prompt (str, optional): System-level prompt to set the context for the conversation.
        question_prompt (str, optional): The main question or user prompt.
        assistant_answer (str, optional): Assistant's previous answer (if any).
        user_prompt (str, optional): User's follow-up prompt (if any).

    Returns:
        str: The response from the GPT model, or None if an error occurs.
    """
    # Initialize the message history as an empty list
    message_history = []
    
    # Add system prompt if provided
    if sys_prompt:
        message_history.append({"role": "system", "content": sys_prompt})
    # Add user prompt (question) if provided
    if question_prompt:
        message_history.append({"role": "user", "content": question_prompt})
    # Add assistant's previous answer if provided
    if assistant_answer:
        message_history.append({"role": "assistant", "content": assistant_answer})
    # Add user's follow-up prompt if provided
    if user_prompt:
        message_history.append({"role": "user", "content": user_prompt})

    try:
        # Call the GPT model with the constructed message history
        completion = client.chat.completions.create(
            model=gpt_model,  # Specify the GPT model to use
            messages=message_history,  # Provide the conversation history
        )

        # Extract data from the API response
        gen_answ_content = completion.choices[0].message.content

        gen_answ_data = {
            "gen_answ_id": completion.id,
            "sys_prompt": sys_prompt,
            "question_prompt": question_prompt,
            "assistant_answer": assistant_answer,
            "user_prompt": user_prompt,
            "gen_answ_content": gen_answ_content,
            "gen_answ_created": completion.created,
            "gen_answ_model": completion.model,
            "gen_answ_completion_tokens": completion.usage.completion_tokens,
            "gen_answ_prompt_tokens": completion.usage.prompt_tokens,
            "gen_answ_total_tokens": completion.usage.total_tokens
        }
        
        # Specify the file name
        convo_file_name = "conversation_history.csv"

        # Perform the operation
        save_to_csv(gen_answ_data, convo_file_name, operation="insert")

        # Return the content of the first choice in the response
        return gen_answ_content
    
    except Exception as e:
        # Log any errors that occur during the API call
        logging.error(f"Une erreur s'est produite lors de l'appel à l'API : {str(e)}")
        return None


# Reads a text file, interacts with GPT to generate a response, and saves the result.
def gpt_prompt(sys_prompt=None, question_prompt=None, assistant_answer=None, user_prompt=None, output_file_name=None):
    """
    Constructs a message history for a GPT conversation, sends it to the GPT model,
    saves the conversation data to a CSV file, and optionally writes only the generated answer
    to a separate text file.

    Args:
        sys_prompt (str, optional): System-level prompt to set the context.
        question_prompt (str, optional): The main question or user prompt.
        assistant_answer (str, optional): Assistant's previous answer (if any).
        user_prompt (str, optional): User's follow-up prompt (if any).
        output_file_name (str, optional): The file path (including name) for storing only the
                                          generated answer (e.g., 'answer.txt'). If not provided,
                                          no .txt file is created.

    Returns:
        str: The response from the GPT model, or None if an error occurs.
    """
    message_history = []
    
    if sys_prompt:
        message_history.append({"role": "system", "content": sys_prompt})
    if question_prompt:
        message_history.append({"role": "user", "content": question_prompt})
    if assistant_answer:
        message_history.append({"role": "assistant", "content": assistant_answer})
    if user_prompt:
        message_history.append({"role": "user", "content": user_prompt})

    try:
        # Call the GPT model with the constructed message history.
        completion = client.chat.completions.create(
            model=gpt_model,  # Specify the GPT model to use
            messages=message_history,
        )

        # Extract the generated answer from the response.
        gen_answ_content = completion.choices[0].message.content

        # Build a dictionary of conversation data.
        gen_answ_data = {
            "gen_answ_id": completion.id,
            "sys_prompt": sys_prompt,
            "question_prompt": question_prompt,
            "assistant_answer": assistant_answer,
            "user_prompt": user_prompt,
            "gen_answ_content": gen_answ_content,
            "gen_answ_created": completion.created,
            "gen_answ_model": completion.model,
            "gen_answ_completion_tokens": completion.usage.completion_tokens,
            "gen_answ_prompt_tokens": completion.usage.prompt_tokens,
            "gen_answ_total_tokens": completion.usage.total_tokens
        }
        
        # Save the full conversation history to a CSV file.
        convo_file_name = "conversation_history.csv"
        save_to_csv(gen_answ_data, convo_file_name, operation="insert")

        # If an output file name is provided, save only the generated answer to that file.
        if output_file_name:
            with open(output_file_name, mode='w', encoding='utf-8') as txt_file:
                txt_file.write(gen_answ_content)
            logging.info(f"Generated answer saved to {output_file_name} successfully.")

        return gen_answ_content

    except Exception as e:
        logging.error(f"An error occurred during the API call: {str(e)}")
        return None



# New to deal with
def lire_contenu_fichier(file_path):
    # Lire le contenu du fichier texte
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            txt_file_content = file.read()
        # Retourner une réponse avec le contenu du fichier
        assistant_answer = f"Oui, voici le contenu du document : {txt_file_content}"
        return assistant_answer
    except FileNotFoundError:
        # Journaliser une erreur si le fichier est introuvable
        logging.error("Le fichier spécifié est introuvable.")
        return "Le fichier spécifié est introuvable."
    except Exception as e:
        # Journaliser toute autre exception qui se produit
        logging.error(f"Une erreur s'est produite : {str(e)}")
        return f"Une erreur s'est produite : {str(e)}"
                    

## Reads a text file, interacts with GPT to generate a response, and saves the result directly into a CSV file.
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


# Function to retrieve all PNG files in the specified folder
def get_png_files_in_subfolders(folder):
    """
    Retrieves all PNG files in the specified folder and its subfolders, 
    and sorts them by the page number extracted from their filenames.

    Args:
        folder (str): Path to the root folder.

    Returns:
        list: A sorted list of PNG file paths based on page numbers.
    """
    png_files = []  # Initialize an empty list to store file paths

    # Walk through the folder and its subfolders
    for root, _, files in os.walk(folder):
        for file in files:
            # Check if the file is a PNG file
            if file.endswith('.png'):
                # Get the full path of the file
                full_path = os.path.join(root, file)
                png_files.append(full_path)  # Add the file path to the list
    
    # Define a helper function to extract the page number from the file name
    def extract_page_number(filename):
        match = re.search(r'page_(\d+)\.png', filename)  # Look for "page_{number}.png"
        return int(match.group(1)) if match else float('inf')  # Return a high value if no number is found

    # Sort PNG files based on the extracted page number
    png_files.sort(key=lambda x: extract_page_number(os.path.basename(x)))
    
    return png_files  # Return the sorted list of PNG file paths

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
