import os
import re
import csv
import logging
import requests
import fitz
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv
import streamlit as st
from utils import *

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

def save_to_csv(dict_data, output_file_name, operation="insert"):
    """
    Saves, updates, or deletes rows in a CSV file.

    Args:
        dict_data (dict): A dictionary containing the dict_data to save (keys as headers, values as rows).
        output_file_name (str): The name of the CSV file to save the dict_data.
        operation (str): The operation to perform - "insert", "update", or "delete".

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
        output_file_name = "conversation_history.csv"

        # Perform the operation
        save_to_csv(gen_answ_data, output_file_name, operation="insert")

        # Return the content of the first choice in the response
        return gen_answ_content
    
    except Exception as e:
        # Log any errors that occur during the API call
        logging.error(f"Une erreur s'est produite lors de l'appel à l'API : {str(e)}")
        return None


#########################################
# Example Usage
#########################################

# Example data
sys_prompt = "System initialization"
question_prompt = "Say hello"
assistant_answer = "Hello, how can I assist you today?"
user_prompt = "What can you do?"

gen_answer = gpt_prompt(sys_prompt=None, question_prompt=question_prompt, assistant_answer=None, user_prompt=None)
gen_answer