import os
import time
import logging
import streamlit as st
from dotenv import load_dotenv
from Utils import input_folder, output_folder, process_pdfs, list_documents, download_document, combine_page_files

# Load environment variables
load_dotenv()

# Streamlit configuration
st.set_page_config(page_title="PDF OCR Processor", layout="wide")

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# User interface
st.title("Title")
st.markdown("""Markdown""")

# File upload
uploaded_file = st.file_uploader("Téléchargez un fichier PDF", type=["pdf"])

if uploaded_file:
    # Save the file to the staging area
    pdf_path = os.path.join(input_folder, uploaded_file.name)
    if not os.path.exists(pdf_path):
        with open(pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

    # Full processing via process_pdfs
    with st.spinner(f"Traitement"):
        try:
            # Step 1: Convert the PDF into images and then perform OCR
            # process_pdfs(input_folder, output_folder)

            # Step 2: Download .txt files from HandwritingOCR.com
            documents = list_documents()

            if not documents:
                st.warning("Aucun document trouvé ou erreur lors de la récupération des documents.")
            else:
                for document in documents:
                    document_id = document.get("document_id")
                    original_file_name = document.get("original_file_name", "document")

                    if document_id:
                        download_document(document_id, original_file_name)

            # Step 3: Combine the downloaded .txt documents
            combine_page_files(output_folder)
            st.success("Votre document PDF a été téléchargé avec succès!")

        except Exception as e:
            st.error("Une erreur s'est produite lors du traitement, du téléchargement ou de la combinaison des fichiers.")
            st.exception(e)
