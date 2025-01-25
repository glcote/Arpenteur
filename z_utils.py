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

# Function to read the content of the text file
def read_text_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        logging.error("Le fichier spécifié est introuvable.")
        return None
    except Exception as e:
        logging.error(f"Une erreur s'est produite : {str(e)}")
        return None

# Function to interact with the GPT API
def interact_with_gpt(file_content, sys_prompt, question_prompt, assistant_answer, user_prompt):
    sys_prompt = ""
    question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
    assistant_answer = f"Oui, voici le contenu du document : {file_content}"
    # user_prompt = ""

    message_history = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": question_prompt},
        {"role": "assistant", "content": assistant_answer},
        {"role": "user", "content": user_prompt}
    ]

    try:
        completion = client.chat.completions.create(
            model = gpt_model,
            messages = message_history,
        )
        return completion
    except Exception as e:
        logging.error(f"Une erreur s'est produite lors de l'appel à l'API : {str(e)}")
        return None

# Function to save results into a CSV file
def save_to_csv(data, output_file_name):
    try:
        with open(output_file_name, mode='w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(data.keys())  # Headers
            writer.writerow(data.values())  # Values
        logging.info(f"Données enregistrées avec succès dans {output_file_name}.")
    except Exception as e:
        logging.error(f"Une erreur s'est produite lors de l'enregistrement du fichier CSV : {str(e)}")

########################################################
# Main function that orchestrates the workflow
########################################################
def gpt_txt_file(txt_file_path, sys_prompt, user_prompt, gpt_model, output_csv_file_name="txt"):
    file_content = read_text_file(txt_file_path)
    if not file_content:
        return "Erreur lors de la lecture du fichier."

    completion = interact_with_gpt(sys_prompt, user_prompt, file_content, gpt_model)
    if not completion:
        return "Erreur lors de l'interaction avec GPT."

    gen_answ_content = completion.choices[0].message.content
    gen_answ_data = {
        "txt_file_path": txt_file_path,
        "sys_prompt": sys_prompt,
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

    save_to_csv(gen_answ_data, output_csv_file_name)
    return gen_answ_content


# Exemple d'appel de la fonction gpt_txt_file
txt_file_path = os.path.join(input_folder, "example.txt")  # Chemin du fichier texte d'entrée
sys_prompt = "Vous êtes un assistant intelligent conçu pour aider à analyser des documents."
user_prompt = "Analysez le contenu du document et fournissez un résumé clair et concis."
output_csv_file_name = os.path.join(output_folder, "output.csv")  # Chemin du fichier CSV de sortie

# Appel à la fonction
result = gpt_txt_file(
    txt_file_path=txt_file_path,
    sys_prompt=sys_prompt,
    user_prompt=user_prompt,
    gpt_model=gpt_model,
    client=client,
    output_csv_file_name=output_csv_file_name
)

# Afficher le résultat généré par GPT
print("Contenu généré par GPT :")
print(result)
