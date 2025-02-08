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

# Define your helper function to display images
def display_images():
    """
    Display images extracted from a PDF file in a Streamlit app.
    
    Parameters:
        uploaded_file: The file object uploaded by the user.
        nb_images: The number of pages/images generated from the PDF.
        image_paths: A list of paths to the generated images.
    """
    with st.spinner("Images en cours..."):
        try:
            # Add a Markdown link to "Voir OCR"
            st.markdown("[Voir OCR](https://www.handwritingocr.com/dashboard)", unsafe_allow_html=True)
            
            if image_paths:
                # Create an expander with the file name and number of pages
                with st.expander(f"{uploaded_file.name} ({nb_images} pages)"):
                    for image_path in image_paths:
                        st.image(image_path, caption=f"Image: {os.path.basename(image_path)}")
            else:
                st.warning("Aucune image n'a été générée.")
        except Exception as e:
            st.error("Une erreur s'est produite lors de la conversion du PDF en images.")
            logging.error(f"Erreur lors de la conversion du PDF : {e}")

def display_resume():
    """
    Generate and display a summary from the given text file content.
    
    Parameters:
        output_file_path_txt (str): The path to the text file containing the document content.
        output_folder (str): The folder where the summary file will be stored.
        file_name (str): The base file name (without extension) used to build the summary file path.
    """
    with st.spinner("Résumé en cours..."):
        with st.expander("Résumé"):
            try:
                # Add a button to refresh the summary
                refresh = st.button("Rafraîchir")

                # Define variables for GPT
                sys_prompt = "Vous êtes un arpenteur et notaire d'experience. Je suis un client."
                question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
                
                # Read the content of the document
                file_content = read_text_file(output_file_path_txt)
                assistant_answer = f"Oui, voici le contenu du document : {file_content}"
                user_prompt = "Parlez-moi de ce document, s'il vous plaît. Soyez précis."
                                
                # If refresh is requested or if the summary file doesn't exist, generate a new summary.
                if refresh or not os.path.exists(summary_file_name):
                    gen_answer = gpt_prompt(sys_prompt, question_prompt, assistant_answer, user_prompt, summary_file_name)
                else:
                    # If the summary already exists and no refresh is requested, read its contents.
                    with open(summary_file_name, "r", encoding="utf-8") as f:
                        gen_answer = f.read()

                st.markdown(gen_answer)
            except Exception as e:
                st.error("Une erreur s'est produite lors de la génération du résumé.")
                logging.error(f"Erreur lors de la génération du résumé : {e}")

def display_qna_saved():
    """
    Display Q&A responses for saved questions using GPT.
    
    Parameters:
        output_folder (str): The folder containing the "Questions_Saved.txt" file.
        summary_file_name (str): The path to the summary file.
        sys_prompt (str): The system prompt for GPT.
        question_prompt (str): The question prompt for GPT.
    """
    
    if os.path.exists(questions_txt_path):
        # Create an expander for Q&A
        with st.expander("Q&A"):
            st.info("Réponses générées pour chaque question sauvegardée")
            
            # Read and clean the list of saved questions
            with open(questions_txt_path, "r", encoding="utf-8") as file:
                # Assume each line is a question (adjust according to your format)
                questions = [line.strip() for line in file.readlines() if line.strip()]
            
            # For each question, request GPT to generate a response
            for question in questions:
                # Read the summary content (adjust according to your logic)
                summary_content = read_text_file(summary_file_name)
                sys_prompt = "Vous êtes un arpenteur et notaire d'experience. Je suis un client."
                question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
                assistant_answer = f"Oui, voici le contenu du document : {summary_content}"
                user_prompt = (
                    f"""En vous basant sur le document, répondez à la question suivante de manière concise.\n
                    Question: {question}\n
                    Réponse:"""
                )
                try:
                    answer = gpt_prompt(sys_prompt, question_prompt, assistant_answer, user_prompt, None)
                except Exception as e:
                    logging.error(f"Erreur lors de la génération de la réponse pour la question '{question}' : {e}")
                    answer = "Erreur lors de la génération de la réponse."
                
                # Display the question and its corresponding answer in Markdown
                st.markdown(f"**Question :** {question}")
                st.markdown(f"**Réponse :** {answer}")
                st.markdown("---")

def display_qna_suggestions():
    """
    Generate and display Q&A suggestions based on a document summary,
    allow the user to select questions, and save them.
    
    Parameters:
        output_folder (str): The folder where output files are stored.
        file_name (str): The base name of the file (without extension).
        summary_file_name (str): The path to the summary file.
    """
    with st.spinner("Q&A en cours..."):
        with st.expander("Q&A Suggestions"):
            st.info("Voici quelques suggestions pour des questions/réponses que vous pouvez ensuite sauvegardez.")
            try:
                # Button to refresh content with a unique key
                refresh = st.button("Rafraîchir", key="refresh_qna_suggestions")

                # Define variables for GPT
                summary_content = read_text_file(summary_file_name)
                sys_prompt = "Vous êtes un arpenteur et notaire d'experience. Je suis un client."
                question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
                assistant_answer = f"Oui, voici le contenu du document : {summary_content}"
                # Note: The original code repeated the assistant_answer; one instance is sufficient.
                user_prompt = (
                    f"""Présentez moi une série de questions concernant le document.
Les réponses doivent se trouver directement dans le texte fourni.
Votre réponse doit être structurées en paires structurées 'Q:' et 'A:'.
Par exemple: 'Q: Quel est votre nom? R: Je m'appelle GPT.'
Éviter les dates dans vos réponse.
Par exemple: 'Q: Quel montant a été lié à l'hypothèque de 2010?' devrait être 'Q: Quel montant a été lié à/aux l'hypothèque(s)?'
Veuiller mettre les questions en gras svp."""
                )
                
                # Build the file name for the suggested Q&A
                questions_file_name = os.path.join(output_folder, file_name, f"{file_name}_Q&A_Suggested.txt")
                
                # If refresh is requested or the file doesn't exist, generate a new version
                if refresh or not os.path.exists(questions_file_name):
                    gen_answer = gpt_prompt(sys_prompt, question_prompt, assistant_answer, user_prompt, questions_file_name)
                else:
                    # Otherwise, read its content
                    with open(questions_file_name, "r", encoding="utf-8") as f:
                        gen_answer = f.read()
                
                # Display the generated text as Markdown
                st.markdown(gen_answer)

                ###############################################
                # Extraction and Saving of Q&A
                ###############################################
                
                # Extract Q&A pairs using a regular expression
                qa_pairs = re.findall(r"Q\s?:\s*(.*?)\s*A\s?:\s*(.*?)(?=\n.+Q\s?:|\Z)", gen_answer, re.DOTALL)
                
                if qa_pairs:
                    # Format the questions for display in a multiselect widget
                    options = [q.strip().replace('**', '') for q, a in qa_pairs]
                    
                    # Allow multiple questions to be selected
                    selected_question = st.multiselect(
                        "Question(s) sauvegardée(s)",
                        options,
                        key="multi_qna"
                    )
                    
                    # Button to save the selected questions, with a unique key
                    if st.button("Sauvegarder la sélection", key="save_selected_qna"):
                        if selected_question:
                            # Build the file path to save the questions
                            question_file_name = os.path.join(output_folder, "Questions_Saved.txt")
                            save_to_txt(selected_question, question_file_name, operation="insert")
                            st.success("Les questions ont été sauvegardées !")
                        else:
                            st.warning("Veuillez sélectionner au moins une question avant de sauvegarder.")
                else:
                    st.warning("Aucune question n'a pu être extraite du texte généré.")
                        
            except Exception as e:
                st.error("Une erreur s'est produite lors de la génération des questions suggérées.")
                logging.error(f"Erreur lors de la génération des Q&A : {e}")


########################################
# PDF -> Image -> OCR -> TXT -> LOOP(GPT) -> Action!
########################################

if uploaded_file:
    # Extract file name without the ".pdf" extension
    file_name = re.sub(r"\.pdf$", "", uploaded_file.name)
    
    # Define the input and output file paths
    input_file_path = os.path.join(input_folder, uploaded_file.name)
    output_file_path_pdf = os.path.join(output_folder, file_name, file_name + ".pdf")
    output_file_path_txt = os.path.join(output_folder, file_name, file_name + "_Combine.txt")
    summary_file_name = os.path.join(output_folder, file_name, f"{file_name}_Resume.txt")
    summary_content = read_text_file(summary_file_name)
    questions_txt_path = os.path.join(output_folder, "Questions_Saved.txt")
    
    # Check if the file (or folder) already exists in output_folder or its subfolders
    file_exists = False
    for root, dirs, files in os.walk(output_folder):
        if file_name in dirs or file_name in files:
            file_exists = True
            break

    try:
        image_paths = pdf_to_images(input_folder, uploaded_file.name, output_folder)
        nb_images = len(image_paths)

        # Step 1: Upload and save the PDF
        save_uploaded_file(uploaded_file, input_file_path, output_file_path_pdf)

        # Step 2: Process the PDF for OCR and Download .txt files
        if not file_exists:

            # Process the PDF for OCR
            with st.spinner("Traitement OCR du PDF..."):
                pdf_to_ocr(input_file_path, output_folder)

            # Download .txt files (wait time based on the number of images)
            nb_secondes = 10 * nb_images
            time.sleep(nb_secondes)
            with st.spinner(f"Téléchargement des {nb_images} fichiers .txt ({nb_secondes}s)..."):
                ocr_list_download_combine_txt_file()
 
        # Step 3: Convert the PDF to images and save the generated images
        display_images()

        # Step 4: Display 
        display_resume()
        display_qna_saved()
        display_qna_suggestions()

    except Exception as e:
        st.error("Une erreur s'est produite lors du traitement du PDF.")
        st.exception(e)

    # ########################################
    # # Expender "Q&A"
    # ########################################
    # with st.spinner("Q&A en cours..."):
    #     with st.expander("Q&A Suggestions"):
    #         st.info("Voici quelques suggestions pour des questions/réponses que vous pouvez ensuite sauvegardez.")
    #         try:
    #             # Bouton pour rafraîchir le contenu, avec une clé unique
    #             refresh = st.button("Rafraîchir", key="refresh_qna_suggestions")

    #             # Définir les variables pour GPT
    #             summary_content = read_text_file(summary_file_name)
    #             sys_prompt = "Vous êtes un arpenteur et notaire d'experience. Je suis un client."
    #             question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
    #             assistant_answer = f"Oui, voici le contenu du document : {summary_content}"
    #             assistant_answer = f"Oui, voici le contenu du document : {summary_content}"
    #             user_prompt = """Présentez moi une série de questions concernant le document. 
    #             Les réponses doivent se trouver directement dans le texte fourni. 
    #             Votre réponse doit être structurées en paires structurées 'Q:' et 'A:'. 
    #             Par exemple : 'Q: Quel est votre nom? R: Je m'appelle GPT.'
    #             Éviter les dates dans vos réponse.
    #             Par exemple : 'Q: Quel montant a été lié à l'hypothèque de 2010?' devrait être 'Q: Quel montant a été lié à/aux l'hypothèque(s)?'
    #             Veuiller mettre les questions en gras svp."""
                
    #             questions_file_name = f"{output_folder}/{file_name}/{file_name}_Q&A_Suggested.txt"
                
    #             # Si rafraîchissement demandé ou si le fichier n'existe pas, générer une nouvelle version
    #             if refresh or not os.path.exists(questions_file_name):
    #                 gen_answer = gpt_prompt(sys_prompt, question_prompt, assistant_answer, user_prompt, questions_file_name)
    #             else:
    #                 # Sinon, lire son contenu
    #                 with open(questions_file_name, "r", encoding="utf-8") as f:
    #                     gen_answer = f.read()
                
    #             # Afficher le texte généré en Markdown
    #             st.markdown(gen_answer)

    #             ###############################################
    #             # Extraction et sauvegarde de Q&A
    #             ###############################################

    #             # Extraction des paires Q&A avec une expression régulière
    #             qa_pairs = re.findall(r"Q\s?:\s*(.*?)\s*A\s?:\s*(.*?)(?=\n.+Q\s?:|\Z)", gen_answer, re.DOTALL) # Question
    #             # question_list = re.findall(r"Q\s?:\s*(.*?)\s*A\s?:\s*(.*?)(?=\n.+Q\s?:|\Z)", gen_answer, re.DOTALL)
    #             # answer_list = re.findall(r"Q\s?:\s*(.*?)\s*A\s?:\s*(.*?)(?=\n.+Q\s?:|\Z)", gen_answer, re.DOTALL)

    #             if qa_pairs:
    #                 # Formatage des paires pour l'affichage dans le multiselect
    #                 options = [f"{q.strip().replace('**', '')}" for q, a in qa_pairs]
                    
    #                 # Sélection multiple
    #                 selected_question = st.multiselect(
    #                     "Question(s) sauvegardée(s)",
    #                     options,
    #                     key="multi_qna"
    #                 )
                    
    #                 # Bouton pour sauvegarder la sélection, avec une clé unique
    #                 if st.button("Sauvegarder la sélection", key="save_selected_qna"):
    #                     if selected_question:
    #                         question_file_name = os.path.join(output_folder, f"Questions_Saved.txt")
    #                         save_to_txt(selected_question, question_file_name, operation="insert")
    #                         st.success("Les questions ont été sauvegardées !")
    #                     else:
    #                         st.warning("Veuillez sélectionner au moins un question avant de sauvegarder.")
    #             else:
    #                 st.warning("Aucune question n'a pu être extraite du texte généré.")
                        
    #         except Exception as e:
    #             st.error("Une erreur s'est produite lors de la génération des questions suggérées.")
    #             logging.error(f"Erreur lors de la génération des Q&A : {e}")

# ########################################
# # GPT Interaction
# ########################################

#     # Initialize the session state variable if it doesn't exist
#     if "generated_answer" not in st.session_state:
#         st.session_state.generated_answer = ""

#     user_prompt = st.text_area("Je suis expert notaire et arpenteur-géomètre", placeholder="Posez ici votre question...")

#     # Button to generate the response
#     if st.button("Générer la réponse"):
#         generated_answer = gpt_prompt(sys_prompt, question_prompt, assistant_answer, user_prompt, None)
#         st.session_state.generated_answer = generated_answer

#     # Button to save the question (and/or response if they exist)
#     if st.session_state.generated_answer or user_prompt:
#         if st.button("Enregistrer la question"):
#             answer_file_path = os.path.join(output_folder, "Questions_Saved.txt")
#             try:
#                 save_to_txt(user_prompt, answer_file_path, operation="insert")
#             except Exception as e:
#                 st.error(f"Erreur lors de l'enregistrement : {e}")

#     # Always display the generated answer if it exists
#     if st.session_state.generated_answer:
#         st.markdown("### Réponse Générée")
#         st.write(st.session_state.generated_answer)

