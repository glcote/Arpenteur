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
st.title("Title")
st.markdown("Description")

# File upload section
uploaded_file = st.file_uploader("Téléchargez un fichier PDF", type=["pdf"])

########################################
# PDF -> Image -> OCR -> TXT 
########################################

if uploaded_file:
    # Extraire le nom de fichier sans l'extension ".pdf"
    file_name = re.sub(r"\.pdf$", "", uploaded_file.name)
    
    # Définir les chemins d'entrée et de sortie
    input_file_path = os.path.join(input_folder, uploaded_file.name)
    output_file_path_pdf = os.path.join(output_folder, file_name, file_name + ".pdf")
    output_file_path_txt = os.path.join(output_folder, file_name, file_name + "_Combine.txt")
    
    try:
        # Sauvegarder le fichier téléchargé dans le dossier spécifié
        with open(input_file_path, "wb") as input_file:
            input_file.write(uploaded_file.getbuffer())
        logging.info(f"File saved : {input_file_path}")
        
        # Sauvegarder une copie dans le dossier de sortie
        os.makedirs(os.path.dirname(output_file_path_pdf), exist_ok=True)  # Crée le sous-dossier si nécessaire
        with open(output_file_path_pdf, "wb") as output_file:
            output_file.write(uploaded_file.getbuffer())
        logging.info(f"File saved : {output_file_path_pdf}")
    
    except Exception as e:
        # Gérer les erreurs pendant la sauvegarde
        st.error("Une erreur s'est produite lors de la sauvegarde du fichier.")
        logging.error(f"Erreur lors de la sauvegarde du fichier : {e}")

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
# Expender ".pdf (pages)"
########################################

    with st.spinner("Images en cours..."):
        # Convert the uploaded PDF file to images
        try:
            # Ajouter un lien Markdown "Voir OCR"
            st.markdown("[Voir OCR](https://www.handwritingocr.com/dashboard)", unsafe_allow_html=True)

            # Call the function to convert the PDF to images and store the paths of the generated images
            image_paths = pdf_to_images(input_folder, uploaded_file.name, output_folder)
            
            if image_paths:
                # Create a dropdown menu using st.expander
                with st.expander(f"{uploaded_file.name} ({len(image_paths)} pages)"):
                    # Display each generated image in the UI within the dropdown
                    for image_path in image_paths:
                        st.image(image_path, caption=f"Image: {os.path.basename(image_path)}")
            else:
                st.warning("Aucune image n'a été générée.")
        except Exception as e:
            st.error("Une erreur s'est produite lors de la conversion du PDF en images.")
            logging.error(f"Erreur lors de la conversion du PDF : {e}")

########################################
# Expender "Resumé"
########################################
    with st.spinner("Résumé en cours..."):
        with st.expander("Résumé"):
            try:
            # Add a button to refresh the résumé
                refresh = st.button("Rafraîchir le résumé")
                # Define variables for GPT
                sys_prompt = "Vous êtes un arpenteur et notaire d'experience. Je suis un client."
                question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
                file_content = read_text_file(output_file_path_txt)
                assistant_answer = f"Oui, voici le contenu du document : {file_content}"
                user_prompt = "Parlez-moi de ce document, s'il vous plaît. Soyez précis."
                
                answ_prompt_file_name = f"{output_folder}/{file_name}/{file_name}_Resume.txt"
                
                # If refresh is requested or if the file doesn't exist, generate a new résumé
                if refresh or not os.path.exists(answ_prompt_file_name):
                    gen_answer = gpt_prompt(sys_prompt, question_prompt, assistant_answer, user_prompt, answ_prompt_file_name)
                else:
                    # If the file exists and no refresh is requested, read its contents
                    with open(answ_prompt_file_name, "r", encoding="utf-8") as f:
                        gen_answer = f.read()

                st.markdown(gen_answer)
            except Exception as e:
                st.error("Une erreur s'est produite lors de la conversion du PDF en images.")
                logging.error(f"Erreur lors de la conversion du PDF : {e}")

########################################
# Expender "Questions sauvegardées"
########################################
    # Chemin complet vers le fichier Questions_Saved.txt
    questions_saved_path = os.path.join(output_folder, "Questions_Saved.txt")
    if os.path.exists(questions_saved_path):
        with st.spinner("Traitement des questions sauvegardées..."):
            with st.expander("Questions sauvegardées"):
                try:
                    questions_content = read_text_file(questions_saved_path)
                    generated_answer = gpt_prompt(None, f"Formater ces questions svp. Rététez les comme telles. Débuter votre réponse par Voici vos questions sauvegardées : {questions_content}", None, None, None)
                    st.markdown(generated_answer)
                    generated_answer = gpt_prompt(sys_prompt, question_prompt, assistant_answer, questions_content, None)
                    st.markdown(generated_answer)
                except Exception as e:
                    st.error("Une erreur s'est produite lors du traitement des questions sauvegardées.")
                    logging.error(f"Erreur lors du traitement des questions sauvegardées : {e}")

########################################
# GPT Interaction
########################################

    # Initialize the session state variable if it doesn't exist
    if "generated_answer" not in st.session_state:
        st.session_state.generated_answer = ""

    user_prompt = st.text_area("Je suis expert notaire et arpenteur-géomètre", placeholder="Posez ici votre question...")

    # Button to generate the response
    if st.button("Générer la réponse"):
        generated_answer = gpt_prompt(sys_prompt, question_prompt, assistant_answer, user_prompt, None)
        st.session_state.generated_answer = generated_answer

    # Button to save the question (and/or response if they exist)
    if st.session_state.generated_answer or user_prompt:
        if st.button("Enregistrer la question"):
            answer_file_path = os.path.join(output_folder, "Questions_Saved.txt")
            try:
                save_to_txt(user_prompt, answer_file_path, operation="insert")
            except Exception as e:
                st.error(f"Erreur lors de l'enregistrement : {e}")

    # Always display the generated answer if it exists
    if st.session_state.generated_answer:
        st.markdown("### Réponse Générée")
        st.write(st.session_state.generated_answer)

