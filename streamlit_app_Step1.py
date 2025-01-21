import os
import streamlit as st
from Arpenteur_Step1_Handling_OCR import process_pdfs

# Configuration Streamlit
st.set_page_config(page_title="PDF OCR Processor", layout="wide")

# Configuration des dossiers
input_folder = "Document_du_Registre_Foncier"
output_folder = "Document_du_Registre_Foncier_PNG"
os.makedirs(input_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

# Interface utilisateur
st.title("PDF to OCR")
st.markdown("""
Téléchargez un fichier PDF pour :
1. Extraire les images.
2. Effectuer une reconnaissance d'écriture manuscrite.
Les fichiers traités seront disponibles dans le dossier de sortie.
""")

# Téléchargement de fichier
uploaded_file = st.file_uploader("Téléchargez un fichier PDF", type=["pdf"])

if uploaded_file:
    # Enregistrer le fichier dans le dossier d'entrée
    pdf_path = os.path.join(input_folder, uploaded_file.name)
    with open(pdf_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success(f"Le fichier a été enregistré dans : {pdf_path}")

    # Traitement complet via process_pdfs
    st.write("Traitement complet du PDF...")
    with st.spinner(f"Conversion et transcription en cours pour {uploaded_file.name}..."):
        try:
            process_pdfs(input_folder, output_folder)
            st.success("Le PDF a été entièrement traité. Consultez les résultats dans le dossier de sortie.")
        except Exception as e:
            st.error(f"Une erreur s'est produite lors du traitement : {e}")
