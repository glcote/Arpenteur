import os
import re
import time
import logging
import streamlit as st
from dotenv import load_dotenv
from utils import *

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
# PDF -> Image -> OCR -> TXT -> LOOP(GPT) -> Action!
########################################

if uploaded_file:
    # Extraire le nom de fichier sans l'extension ".pdf"
    file_name = re.sub(r"\.pdf$", "", uploaded_file.name)
    
    # Définir les chemins d'entrée et de sortie
    input_file_path = os.path.join(input_folder, uploaded_file.name)
    output_file_path_pdf = os.path.join(output_folder, file_name, file_name + ".pdf")
    output_file_path_txt = os.path.join(output_folder, file_name, file_name + "_Combine.txt")
    
    # Vérifier si file_name existe déjà dans output_folder ou l'un de ses sous-dossiers
    file_exists = False
    for root, dirs, files in os.walk(output_folder):
        # On vérifie dans les noms des dossiers et des fichiers
        if file_name in dirs or file_name in files:
            file_exists = True
            break

    try:
        if not file_exists:
            # Step 1: Upload and save the PDF
            with st.spinner("Étape 1: Téléchargement et enregistrement du PDF..."):
                save_uploaded_file(uploaded_file, input_file_path, output_file_path_pdf)

            # Step 2: Process PDFs to OCR 
            with st.spinner("Étape 2: Traitement OCR du PDF..."):
                pdf_to_ocr(input_folder, output_folder)

            # Step 3: Download .txt files 
            with st.spinner("Étape 3: Téléchargement des fichiers .txt..."):
                time.sleep(60)
                ocr_list_download_combine_txt_file()

            # Step 4: Convert the PDF to images and save generated images
            with st.spinner("Étape 4: Conversion du PDF en images..."):
                image_paths = pdf_to_images(input_folder, uploaded_file.name, output_folder)
        else:
            logging.info(f"Le fichier '{file_name}' existe déjà dans {output_folder}. OCR est sauté.")             
        
    except Exception as e:
        st.error("Une erreur s'est produite lors du traitement, du téléchargement ou de la combinaison des fichiers.")
        st.exception(e)

    ########################################
    # Expender ".pdf (pages)"
    ########################################

    # with st.spinner("Images en cours..."):
    #     # Convert the uploaded PDF file to images
    #     try:
    #         # Ajouter un lien Markdown "Voir OCR"
    #         st.markdown("[Voir OCR](https://www.handwritingocr.com/dashboard)", unsafe_allow_html=True)
            
    #         # # Call the function to convert the PDF to images and store the paths of the generated images
    #         # image_paths = pdf_to_images(input_folder, uploaded_file.name, output_folder)
            
    #         if image_paths:
    #             # Create a dropdown menu using st.expander
    #             with st.expander(f"{uploaded_file.name} ({len(image_paths)} pages)"):
    #                 # Display each generated image in the UI within the dropdown
    #                 for image_path in image_paths:
    #                     st.image(image_path, caption=f"Image: {os.path.basename(image_path)}")
    #         else:
    #             st.warning("Aucune image n'a été générée.")
    #     except Exception as e:
    #         st.error("Une erreur s'est produite lors de la conversion du PDF en images.")
    #         logging.error(f"Erreur lors de la conversion du PDF : {e}")

    ########################################
    # Expender "Resumé"
    ########################################

    with st.spinner("Résumé en cours..."):
        with st.expander("Résumé"):
            try:
                # Add a button to refresh the résumé
                refresh = st.button("Rafraîchir")

                # Define variables for GPT
                sys_prompt = "Vous êtes un arpenteur et notaire d'experience. Je suis un client."
                question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
                file_content = read_text_file(output_file_path_txt)
                assistant_answer = f"Oui, voici le contenu du document : {file_content}"
                user_prompt = "Parlez-moi de ce document, s'il vous plaît. Soyez précis."
                
                summary_file_name = f"{output_folder}/{file_name}/{file_name}_Resume.txt"
                
                # If refresh is requested or if the file doesn't exist, generate a new résumé
                if refresh or not os.path.exists(summary_file_name):
                    gen_answer = gpt_prompt(sys_prompt, question_prompt, assistant_answer, user_prompt, summary_file_name)
                else:
                    # If the file exists and no refresh is requested, read its contents
                    with open(summary_file_name, "r", encoding="utf-8") as f:
                        gen_answer = f.read()

                st.markdown(gen_answer)
            except Exception as e:
                st.error("Une erreur s'est produite lors de la conversion du PDF en images.")
                logging.error(f"Erreur lors de la conversion du PDF : {e}")

    ###############################################
    # Q&A
    ###############################################
    questions_txt_path = os.path.join(output_folder, "Questions_Saved.txt")
    if os.path.exists(questions_txt_path):
        
        # Expander pour les réponses aux questions sauvegardées
        with st.expander("Q&A"):
            st.info("Réponses générées pour chaque question sauvegardée")
            
            # Lire et nettoyer la liste des questions sauvegardées
            with open(questions_txt_path, "r", encoding="utf-8") as file:
                # Supposons que chaque ligne correspond à une question (ajustez selon votre format)
                questions = [line.strip() for line in file.readlines() if line.strip()]
            
            # Pour chaque question, demander à GPT de générer une réponse
            for question in questions:
                # Lire le contenu du résumé (à adapter selon votre logique)
                summary_content = read_text_file(summary_file_name)
                assistant_answer = f"Oui, voici le contenu du document : {summary_content}"
                user_prompt = (
                    f"En vous basant sur le document ci-dessous, répondez à la question suivante de manière concise.\n"
                    f"Question: {question}\n"
                    f"Réponse:"
                )
                try:
                    answer = gpt_prompt(sys_prompt, question_prompt, assistant_answer, user_prompt, None)
                except Exception as e:
                    logging.error(f"Erreur lors de la génération de la réponse pour la question '{question}' : {e}")
                    answer = "Erreur lors de la génération de la réponse."
                
                # Afficher la question et la réponse en Markdown
                st.markdown(f"**Question :** {question}")
                st.markdown(f"**Réponse :** {answer}")
                st.markdown("---")

    ########################################
    # Expender "Q&A"
    ########################################
    with st.spinner("Q&A en cours..."):
        with st.expander("Q&A Suggestions"):
            st.info("Voici quelques suggestions pour des questions/réponses que vous pouvez ensuite sauvegardez.")
            try:
                # Bouton pour rafraîchir le contenu, avec une clé unique
                refresh = st.button("Rafraîchir", key="refresh_qna_suggestions")

                # Définir les variables pour GPT
                summary_content = read_text_file(summary_file_name)
                assistant_answer = f"Oui, voici le contenu du document : {summary_content}"
                user_prompt = """Présentez moi une série de questions concernant le document. 
                Les réponses doivent se trouver directement dans le texte fourni. 
                Votre réponse doit être structurées en paires structurées 'Q:' et 'A:'. 
                Par exemple : 'Q: Quel est votre nom? R: Je m'appelle GPT.'
                Éviter les dates dans vos réponse.
                Par exemple : 'Q: Quel montant a été lié à l'hypothèque de 2010?' devrait être 'Q: Quel montant a été lié à/aux l'hypothèque(s)?'
                Veuiller mettre les questions en gras svp."""
                
                questions_file_name = f"{output_folder}/{file_name}/{file_name}_Q&A_Suggested.txt"
                
                # Si rafraîchissement demandé ou si le fichier n'existe pas, générer une nouvelle version
                if refresh or not os.path.exists(questions_file_name):
                    gen_answer = gpt_prompt(sys_prompt, question_prompt, assistant_answer, user_prompt, questions_file_name)
                else:
                    # Sinon, lire son contenu
                    with open(questions_file_name, "r", encoding="utf-8") as f:
                        gen_answer = f.read()
                
                # Afficher le texte généré en Markdown
                st.markdown(gen_answer)

                ###############################################
                # Extraction et sauvegarde de Q&A
                ###############################################

                # Extraction des paires Q&A avec une expression régulière
                qa_pairs = re.findall(r"Q\s?:\s*(.*?)\s*A\s?:\s*(.*?)(?=\n.+Q\s?:|\Z)", gen_answer, re.DOTALL) # Question
                # question_list = re.findall(r"Q\s?:\s*(.*?)\s*A\s?:\s*(.*?)(?=\n.+Q\s?:|\Z)", gen_answer, re.DOTALL)
                # answer_list = re.findall(r"Q\s?:\s*(.*?)\s*A\s?:\s*(.*?)(?=\n.+Q\s?:|\Z)", gen_answer, re.DOTALL)

                if qa_pairs:
                    # Formatage des paires pour l'affichage dans le multiselect
                    options = [f"{q.strip().replace('**', '')}" for q, a in qa_pairs]
                    
                    # Sélection multiple
                    selected_question = st.multiselect(
                        "Question(s) sauvegardée(s)",
                        options,
                        key="multi_qna"
                    )
                    
                    # Bouton pour sauvegarder la sélection, avec une clé unique
                    if st.button("Sauvegarder la sélection", key="save_selected_qna"):
                        if selected_question:
                            question_file_name = os.path.join(output_folder, f"Questions_Saved.txt")
                            save_to_txt(selected_question, question_file_name, operation="insert")
                            st.success("Les questions ont été sauvegardées !")
                        else:
                            st.warning("Veuillez sélectionner au moins un question avant de sauvegarder.")
                else:
                    st.warning("Aucune question n'a pu être extraite du texte généré.")
                        
            except Exception as e:
                st.error("Une erreur s'est produite lors de la génération des questions suggérées.")
                logging.error(f"Erreur lors de la génération des Q&A : {e}")

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

