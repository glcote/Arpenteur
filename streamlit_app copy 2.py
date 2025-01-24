import os
import time
import logging
import streamlit as st
from dotenv import load_dotenv
from Utils import input_folder, output_folder, process_pdfs, list_documents, download_document

# Charger les variables d'environnement
load_dotenv()

# Configuration Streamlit
st.set_page_config(page_title="PDF OCR Processor", layout="wide")

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Interface utilisateur
st.title("PDF to OCR and Document Download")
st.markdown("""
### Étape 1 : Conversion PDF vers OCR
Téléchargez un fichier PDF pour extraire des images et effectuer la reconnaissance d'écriture manuscrite.

### Étape 2 : Téléchargement des documents générés
Les documents seront automatiquement téléchargés après 1 minute.
""")

# Téléchargement de fichier
uploaded_file = st.file_uploader("Téléchargez un fichier PDF", type=["pdf"])

if uploaded_file:
    # Enregistrer le fichier dans le dossier d'entrée
    pdf_path = os.path.join(input_folder, uploaded_file.name)
    if not os.path.exists(pdf_path):
        with open(pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"Le fichier a été enregistré dans : {pdf_path}")

    # Traitement complet via process_pdfs
    st.write("Traitement complet du PDF...")
    with st.spinner(f"Conversion et transcription en cours pour {uploaded_file.name}..."):
        try:
            process_pdfs(input_folder, output_folder)
            st.success("Le PDF a été entièrement traité.")
            st.info(f"Les résultats sont disponibles dans le dossier : `{output_folder}`")

            # Délai avant d'exécuter la seconde étape
            st.write("Attente de 1 minute avant de démarrer la seconde étape...")
            time.sleep(60)  # Attente de 60 secondes

            # Étape 2 : Télécharger les documents
            st.write("Démarrage du téléchargement des documents...")
            st.info("Récupération de la liste des documents...")
            documents = list_documents()

            if not documents:
                st.warning("Aucun document trouvé ou erreur lors de la récupération des documents.")
            else:
                for document in documents:
                    document_id = document.get("document_id")
                    original_file_name = document.get("original_file_name", "document")

                    if document_id:
                        st.write(f"Téléchargement du document : {original_file_name}")
                        download_document(document_id, original_file_name)

                st.success("Tous les documents ont été téléchargés avec succès !")
        except Exception as e:
            st.error("Une erreur s'est produite lors du traitement ou du téléchargement.")
            st.exception(e)
