import streamlit as st
import os
import logging
from dotenv import load_dotenv
from Arpenteur_Step2_Download_Doc import list_documents, download_document

# Charger les variables d'environnement
load_dotenv()

# Configurer le logging pour Streamlit
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Dossiers
output_folder = "Document_du_Registre_Foncier_PNG"
os.makedirs(output_folder, exist_ok=True)

# Titre de l'application
st.title("Téléchargement des Documents - Arpenteur")

# Description
st.markdown("""
Cette application permet de télécharger tous les documents disponibles via l'API Handwriting OCR.
Cliquez sur le bouton ci-dessous pour démarrer le processus.
""")

# Bouton pour démarrer le téléchargement
if st.button("Télécharger les fichiers"):
    try:
        # Étape 1 : Récupérer les documents depuis l'API
        st.info("Récupération de la liste des documents en cours...")
        documents = list_documents()  # Appel à la fonction depuis votre script
        
        if not documents:
            st.warning("Aucun document trouvé ou erreur lors de la récupération des documents.")
        else:
            # Étape 2 : Télécharger chaque document
            for document in documents:
                document_id = document.get("document_id")
                original_file_name = document.get("original_file_name", "document")
                
                if document_id:
                    st.write(f"Téléchargement du document : {original_file_name}")
                    download_document(document_id, original_file_name)
            
            st.success("Tous les documents ont été téléchargés avec succès !")
    except Exception as e:
        st.error(f"Une erreur s'est produite : {e}")
