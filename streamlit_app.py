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

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Streamlit configuration
st.set_page_config(page_title="PDF OCR Processor & Analyzer", layout="wide")

# Application title & description
st.title("PDF OCR Processor & Analyzer")
st.markdown("Ce portail vous permet de convertir un PDF en images, de traiter l'OCR, de générer un résumé via GPT, et de travailler avec des Q&A. Exécutez chaque étape au besoin.")

# -------------------------------
# Initialize session state variables
# -------------------------------
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None
if "file_name" not in st.session_state:
    st.session_state.file_name = None
if "input_file_path" not in st.session_state:
    st.session_state.input_file_path = None
if "output_file_path_pdf" not in st.session_state:
    st.session_state.output_file_path_pdf = None
if "output_file_path_txt" not in st.session_state:
    st.session_state.output_file_path_txt = None
if "images" not in st.session_state:
    st.session_state.images = None
if "ocr_processed" not in st.session_state:
    st.session_state.ocr_processed = False
if "ocr_text" not in st.session_state:
    st.session_state.ocr_text = None
if "summary" not in st.session_state:
    st.session_state.summary = None
if "qna_suggestions" not in st.session_state:
    st.session_state.qna_suggestions = None
if "generated_answer" not in st.session_state:
    st.session_state.generated_answer = ""

# -------------------------------
# Step 1: File Upload
# -------------------------------
uploaded_file = st.file_uploader("Téléchargez un fichier PDF", type=["pdf"])
if uploaded_file:
    st.session_state.uploaded_file = uploaded_file
    # Extract file name without the .pdf extension
    file_name = re.sub(r"\.pdf$", "", uploaded_file.name)
    st.session_state.file_name = file_name

    # Define input and output paths
    input_file_path = os.path.join(input_folder, uploaded_file.name)
    output_file_path_pdf = os.path.join(output_folder, file_name, file_name + ".pdf")
    output_file_path_txt = os.path.join(output_folder, file_name, file_name + "_Combine.txt")
    
    st.session_state.input_file_path = input_file_path
    st.session_state.output_file_path_pdf = output_file_path_pdf
    st.session_state.output_file_path_txt = output_file_path_txt

    # Save the uploaded file if not already saved
    if not os.path.exists(input_file_path):
        try:
            with open(input_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            logging.info(f"File saved : {input_file_path}")
            st.success(f"Fichier téléchargé et sauvegardé : {input_file_path}")
        except Exception as e:
            st.error("Erreur lors de la sauvegarde du fichier.")
            logging.error(f"Erreur lors de la sauvegarde du fichier : {e}")

    # Save a copy in the output folder if not exists
    os.makedirs(os.path.dirname(output_file_path_pdf), exist_ok=True)
    if not os.path.exists(output_file_path_pdf):
        try:
            with open(output_file_path_pdf, "wb") as f:
                f.write(uploaded_file.getbuffer())
            logging.info(f"File saved : {output_file_path_pdf}")
        except Exception as e:
            st.error("Erreur lors de la sauvegarde du fichier dans le dossier de sortie.")
            logging.error(f"Erreur lors de la sauvegarde du fichier dans le dossier de sortie : {e}")

# -------------------------------
# Step 2: OCR Processing (Download/Combine TXT)
# -------------------------------
if st.session_state.uploaded_file and st.button("Exécuter OCR (Télécharger et Combiner TXT)"):
    with st.spinner("Traitement OCR en cours..."):
        try:
            ocr_list_download_combine_txt_file()
            if os.path.exists(st.session_state.output_file_path_txt):
                st.session_state.ocr_text = read_text_file(st.session_state.output_file_path_txt)
                st.session_state.ocr_processed = True
                st.success("OCR traité et texte combiné disponible.")
            else:
                st.error("Le fichier OCR combiné n'a pas été trouvé.")
        except Exception as e:
            st.error("Erreur lors du traitement OCR.")
            logging.error(f"Erreur OCR: {e}")

# -------------------------------
# Step 3: Convert PDF to Images
# -------------------------------
if st.session_state.uploaded_file and st.button("Convertir PDF en Images"):
    with st.spinner("Conversion en images..."):
        try:
            # Add a markdown link to the OCR dashboard if needed
            st.markdown("[Voir OCR](https://www.handwritingocr.com/dashboard)", unsafe_allow_html=True)
            images = pdf_to_images(input_folder, st.session_state.uploaded_file.name, output_folder)
            if images:
                st.session_state.images = images
                st.success(f"Conversion terminée : {len(images)} pages.")
            else:
                st.warning("Aucune image n'a été générée.")
        except Exception as e:
            st.error("Erreur lors de la conversion du PDF en images.")
            logging.error(f"Erreur lors de la conversion du PDF : {e}")

# Display generated images if available
if st.session_state.images:
    with st.expander(f"{st.session_state.uploaded_file.name} ({len(st.session_state.images)} pages)"):
        for image_path in st.session_state.images:
            st.image(image_path, caption=f"Image : {os.path.basename(image_path)}")

# -------------------------------
# Step 4: Generate Summary using GPT
# -------------------------------
if st.session_state.ocr_processed and st.session_state.ocr_text and st.button("Générer Résumé (GPT)"):
    with st.spinner("Génération du résumé en cours..."):
        try:
            sys_prompt = "Vous êtes un arpenteur et notaire d'experience. Je suis un client."
            question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
            assistant_answer = f"Oui, voici le contenu du document : {st.session_state.ocr_text}"
            user_prompt = "Parlez-moi de ce document, s'il vous plaît. Soyez précis."
            summary_file_name = os.path.join(output_folder, st.session_state.file_name, st.session_state.file_name + "_Resume.txt")
            st.session_state.summary = gpt_prompt(sys_prompt, question_prompt, assistant_answer, user_prompt, summary_file_name)
            st.success("Résumé généré.")
        except Exception as e:
            st.error("Erreur lors de la génération du résumé.")
            logging.error(f"Erreur GPT résumé : {e}")

# Display summary if available
if st.session_state.summary:
    with st.expander("Résumé"):
        st.markdown(st.session_state.summary)

# -------------------------------
# Step 5: Q&A Based on Saved Questions
# -------------------------------
questions_txt_path = os.path.join(output_folder, "Questions_Saved.txt")
if os.path.exists(questions_txt_path):
    with st.expander("Q&A"):
        st.info("Réponses générées pour chaque question sauvegardée")
        try:
            with open(questions_txt_path, "r", encoding="utf-8") as file:
                questions = [line.strip() for line in file.readlines() if line.strip()]
            # Use the generated summary (if available) for context
            summary_content = st.session_state.summary if st.session_state.summary else "Résumé non disponible."
            for question in questions:
                assistant_answer = f"Oui, voici le contenu du document : {summary_content}"
                # Build a specific user prompt for the question
                user_prompt_q = (
                    f"En vous basant sur le document ci-dessous, répondez à la question suivante de manière concise.\n"
                    f"Question: {question}\nRéponse:"
                )
                try:
                    answer = gpt_prompt(sys_prompt, question_prompt, assistant_answer, user_prompt_q, None)
                except Exception as e:
                    logging.error(f"Erreur lors de la génération de la réponse pour la question '{question}': {e}")
                    answer = "Erreur lors de la génération de la réponse."
                st.markdown(f"**Question :** {question}")
                st.markdown(f"**Réponse :** {answer}")
                st.markdown("---")
        except Exception as e:
            st.error("Erreur lors du traitement des questions sauvegardées.")
            logging.error(f"Erreur Q&A: {e}")

# -------------------------------
# Step 6: Q&A Suggestions using GPT
# -------------------------------
if st.session_state.summary and st.button("Générer Q&A Suggestions", key="qna_suggestions"):
    with st.spinner("Génération des suggestions Q&A..."):
        try:
            sys_prompt = "Vous êtes un arpenteur et notaire d'experience. Je suis un client."
            question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
            summary_content = st.session_state.summary
            assistant_answer = f"Oui, voici le contenu du document : {summary_content}"
            user_prompt_qna = """Présentez moi une série de questions concernant le document. 
Les réponses doivent se trouver directement dans le texte fourni. 
Votre réponse doit être structurée en paires 'Q:' et 'A:'. 
Par exemple : 'Q: Quel est votre nom? R: Je m'appelle GPT.'
Évitez d'inclure des dates dans vos réponses.
Veuiller mettre les questions en gras svp."""
            questions_file_name = os.path.join(output_folder, st.session_state.file_name, st.session_state.file_name + "_Q&A_Suggested.txt")
            st.session_state.qna_suggestions = gpt_prompt(sys_prompt, question_prompt, assistant_answer, user_prompt_qna, questions_file_name)
            st.success("Suggestions Q&A générées.")
        except Exception as e:
            st.error("Erreur lors de la génération des suggestions Q&A.")
            logging.error(f"Erreur Q&A Suggestions: {e}")

# Display Q&A suggestions and allow selection for saving
if st.session_state.qna_suggestions:
    with st.expander("Q&A Suggestions"):
        st.markdown(st.session_state.qna_suggestions)
        try:
            # Extract Q&A pairs using regex
            qa_pairs = re.findall(r"Q\s?:\s*(.*?)\s*A\s?:\s*(.*?)(?=\n.+Q\s?:|\Z)", st.session_state.qna_suggestions, re.DOTALL)
            if qa_pairs:
                options = [q.strip().replace('**', '') for q, a in qa_pairs]
                selected_questions = st.multiselect("Question(s) sauvegardée(s)", options, key="multi_qna")
                if st.button("Sauvegarder la sélection", key="save_selected_qna"):
                    if selected_questions:
                        question_file_name = os.path.join(output_folder, "Questions_Saved.txt")
                        save_to_txt(selected_questions, question_file_name, operation="insert")
                        st.success("Les questions ont été sauvegardées !")
                    else:
                        st.warning("Veuillez sélectionner au moins une question avant de sauvegarder.")
            else:
                st.warning("Aucune question n'a pu être extraite du texte généré.")
        except Exception as e:
            st.error("Erreur lors de l'extraction des suggestions Q&A.")
            logging.error(f"Erreur extraction Q&A: {e}")

# -------------------------------
# Step 7: Custom GPT Interaction
# -------------------------------
st.markdown("## Interaction GPT Personnalisée")
user_custom_prompt = st.text_area("Je suis expert notaire et arpenteur-géomètre", placeholder="Posez ici votre question...")
if st.button("Générer la réponse"):
    try:
        # Use the generated summary for context if available
        if st.session_state.summary:
            assistant_answer_custom = f"Oui, voici le contenu du document : {st.session_state.summary}"
        else:
            assistant_answer_custom = "Résumé non disponible."
        sys_prompt = "Vous êtes un arpenteur et notaire d'experience. Je suis un client."
        question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
        generated = gpt_prompt(sys_prompt, question_prompt, assistant_answer_custom, user_custom_prompt, None)
        st.session_state.generated_answer = generated
    except Exception as e:
        st.error("Erreur lors de la génération de la réponse personnalisée.")
        logging.error(f"Erreur GPT custom: {e}")

if st.session_state.generated_answer:
    st.markdown("### Réponse Générée")
    st.write(st.session_state.generated_answer)
