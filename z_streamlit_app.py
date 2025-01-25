import os
import re
import pytz
import logging
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
from utils import (
    input_folder,
    output_folder,
    process_pdfs,
    list_documents,
    download_document,
    combine_page_files,
    txt_file_to_gpt,
    get_combine_txt_files_in_subfolders,
    get_png_files_in_same_folder,
)

# Load environment variables
load_dotenv()

# Streamlit configuration
st.set_page_config(page_title="PDF OCR Processor & Analyzer", layout="wide")

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Application title & description
st.title("PDF OCR Processor & Document Analyzer")
st.markdown("markdown")

########################################
# PDF Ingestion
########################################

# File upload section
uploaded_file = st.file_uploader("Téléchargez un fichier PDF", type=["pdf"])

if uploaded_file:
    uploaded_file_name = re.sub(r"\.pdf", "", uploaded_file.name)
    uploaded_file_path = os.path.join(output_folder, uploaded_file_name, uploaded_file.name)
    if not os.path.exists(uploaded_file_path):
        with open(uploaded_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

    with st.spinner("Téléchargement en cours..."):
        try:
            # # Step 1: Process PDFs
            # process_pdfs(input_folder, output_folder)

            # # Step 2: List and download documents
            # documents = list_documents()

            # if not documents:
            #     st.warning("Aucun document trouvé ou erreur lors de la récupération des documents.")
            # else:
            #     for document in documents:
            #         document_id = document.get("document_id")
            #         file_page_name = document.get("original_file_name", "document")
            #         file_name = re.sub(r"__.+", "", file_page_name)

            #         if document_id:
            #             download_document(document_id, file_name)

            # # Step 3: Combine text files
            # combine_page_files(output_folder)
            # st.success(f"{file_name}.pdf a été téléchargé avec succès!")

            # Step 4: Retrieve and display PNG files
            png_files = get_png_files_in_same_folder(uploaded_file_path)

            if not png_files:
                st.warning("Aucune image PNG trouvée pour ce fichier PDF.")
            else:
                for png_file in png_files:
                    st.image(png_file, caption=os.path.basename(png_file), use_container_width=True)

        except Exception as e:
            st.error("Une erreur s'est produite lors du traitement, du téléchargement ou de la combinaison des fichiers.")
            st.exception(e)

