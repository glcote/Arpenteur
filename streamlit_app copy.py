import os
import re
import pytz
import logging
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
from utils import *

import csv
import requests
import fitz
from PIL import Image
from openai import OpenAI

# Charger les variables d'environnement
load_dotenv()

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Streamlit configuration
st.set_page_config(page_title="PDF OCR Processor & Analyzer", layout="wide")

# Application title & description
st.title("PDF OCR Processor & Document Analyzer")
st.markdown("markdown")

########################################
# PDF Ingestion
########################################

# File upload section
uploaded_file = st.file_uploader("Téléchargez un fichier PDF", type=["pdf"])

if uploaded_file:
    # Extraire le nom de fichier sans l'extension ".pdf"
    file_name = re.sub(r"\.pdf$", "", uploaded_file.name)
    
    # Définir les chemins d'entrée et de sortie
    input_file_path = os.path.join(input_folder, uploaded_file.name)
    output_file_path = os.path.join(output_folder, file_name, uploaded_file.name)
    
    try:
        # Sauvegarder le fichier téléchargé dans le dossier spécifié
        with open(input_file_path, "wb") as input_file:
            input_file.write(uploaded_file.getbuffer())
        logging.info(f"Fichier téléchargé sauvegardé à : {input_file_path}")
        
        # Sauvegarder une copie dans le dossier de sortie
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)  # Crée le sous-dossier si nécessaire
        with open(output_file_path, "wb") as output_file:
            output_file.write(uploaded_file.getbuffer())
        logging.info(f"Copie du fichier sauvegardée à : {output_file_path}")
    
    except Exception as e:
        # Gérer les erreurs pendant la sauvegarde
        st.error("Une erreur s'est produite lors de la sauvegarde du fichier.")
        logging.error(f"Erreur lors de la sauvegarde du fichier : {e}")

########################################
# Background 
########################################

    with st.spinner("Téléchargement en cours..."):
        try:
            # # Step 1: Process PDFs to OCR
            # pdf_to_ocr(input_folder, output_folder)

            # Step 2: Download .txt files
            ocr_list_download_combine_txt_file()
            
        except Exception as e:
            st.error("Une erreur s'est produite lors du traitement, du téléchargement ou de la combinaison des fichiers.")
            st.exception(e)

########################################
# Expender "Voir le fichier"
########################################

    # Convert the uploaded PDF file to images
    try:
        # Call the function to convert the PDF to images and store the paths of the generated images
        image_paths = pdf_to_images(input_folder, uploaded_file.name, output_folder)
        
        if image_paths:
            # Create a dropdown menu using st.expander
            with st.expander(f"Voir {uploaded_file.name}"):
                # Display each generated image in the UI within the dropdown
                for image_path in image_paths:
                    st.image(image_path, caption=f"Image: {os.path.basename(image_path)}")
        else:
            st.warning("Aucune image n'a été générée.")
    except Exception as e:
        st.error("Une erreur s'est produite lors de la conversion du PDF en images.")
        logging.error(f"Erreur lors de la conversion du PDF : {e}")

    # Define variables for GPT
    sys_prompt = ""
    question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
    assistant_answer = f"Oui, voici le contenu du document : {output_file_path}"
    user_prompt = ""

    gen_answer = gpt_prompt(sys_prompt, question_prompt, assistant_answer, user_prompt)

