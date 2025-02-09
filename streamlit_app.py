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
                refresh = st.button("Rafraîchir", key="refresh_resume")

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
    
    The function checks for a saved Q&A file in the output_folder. If the file does not exist 
    or if the user clicks the "Rafraîchir Q&A" button, it regenerates the responses, saves them, 
    and then displays the results.
    
    Assumes the existence of:
        - questions_txt_path: path to the saved questions (one per line).
        - summary_file_name: path to the summary file used as context.
    """

    with st.spinner("Génération des réponses Q&A..."):
        # Create an expander for Q&A content
        with st.expander("Q&A"):
            st.info("Réponses générées pour chaque question sauvegardée")
            
            # Button to refresh (i.e. regenerate) Q&A responses.
            refresh_qna = st.button("Rafraîchir", key="refresh_qna")
            
            # Check if we need to generate new Q&A responses:
            # - if the user clicks refresh, or
            # - if the file does not exist.
            if refresh_qna or not os.path.exists(qna_file_name):
                qna_responses = ""
                
                # Read the saved questions (assuming one question per line)
                if os.path.exists(questions_txt_path):
                    with open(questions_txt_path, "r", encoding="utf-8") as file:
                        questions = [line.strip() for line in file.readlines() if line.strip()]
                else:
                    st.warning("Le fichier des questions sauvegardées est introuvable.")
                    return
                
                # For each question, generate an answer using GPT.
                for question in questions:
                    # Define prompts for GPT 
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
                    
                    # Format the Q&A pair in Markdown
                    qna_responses += f"**{question}**\n\n{answer}\n\n---\n"
                
                # Save the generated Q&A responses for future use.
                try:
                    with open(qna_file_name, "w", encoding="utf-8") as f:
                        f.write(qna_responses)
                except Exception as e:
                    logging.error(f"Erreur lors de la sauvegarde du fichier Q&A : {e}")
            else:
                # If the file exists and refresh was not requested, load its contents.
                try:
                    with open(qna_file_name, "r", encoding="utf-8") as f:
                        qna_responses = f.read()
                except Exception as e:
                    st.error("Erreur lors de la lecture du fichier Q&A sauvegardé.")
                    logging.error(f"Erreur lors de la lecture du fichier Q&A : {e}")
                    return
            
            # Process the text to remove any "Q:" and "A:" markers, similar to the suggestions display
            display_text = re.sub(r"Question\s*:\s*", "", qna_responses)
            display_text = re.sub(r"Réponse\s*:\s*", "", display_text)
            # Finally, display the Q&A responses in Markdown.
            st.markdown(display_text)

def display_qna_suggestions():
    """
    Generate and display Q&A suggestions based on a document summary,
    allow the user to select questions, and save them.
    
    Assumes the existence of:
        - output_folder: folder where output files are stored.
        - file_name: base name of the file (without extension).
        - summary_file_name: path to the summary file.
    """
    with st.expander("Q&A Suggestions"):
        st.info("Voici quelques suggestions pour des questions/réponses que vous pouvez ensuite sauvegarder.")
        try:
            # Button to refresh content with a unique key
            refresh = st.button("Rafraîchir", key="refresh_qna_suggestions")

            # Define variables for GPT
            summary_content = read_text_file(summary_file_name)
            sys_prompt = "Vous êtes un arpenteur et notaire d'experience. Je suis un client."
            question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
            assistant_answer = f"Oui, voici le contenu du document : {summary_content}"
            user_prompt = (
                f"""Présentez moi une série de questions concernant le document.
Les réponses doivent se trouver directement dans le texte fourni.
Votre réponse doit être structurée en paires avec les marqueurs 'Q:' et 'A:'.
Par exemple: 'Q: Quel est votre nom? R: Je m'appelle GPT.'
Éviter les dates dans vos réponse.
Par exemple: 'Q: Quel montant a été lié à l'hypothèque de 2010?' devrait être 'Q: Quel montant a été lié à/aux l'hypothèque(s)?'
Veuillez mettre les questions en gras svp."""
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
            
            # Extract Q&A pairs using a regular expression.
            # The regex looks for text following a "Q:" marker up to an "A:" marker,
            # and then grabs the answer up until the next Q: or the end of the string.
            qa_pairs = re.findall(
                r"Q\s?:\s*(.*?)\s*A\s?:\s*(.*?)(?=\n.+Q\s?:|\Z)",
                gen_answer,
                re.DOTALL
            )
            
            if qa_pairs:
                # Build the Markdown string with the same format as in display_qna_saved()
                qna_responses = ""
                for question, answer in qa_pairs:
                    qna_responses += f"**{question.strip()}**\n\n{answer.strip()}\n\n---\n"
                
                # Display the formatted Q&A pairs
                st.markdown(qna_responses)
                
                ###############################################
                # Extraction and Saving of Q&A
                ###############################################
                
                # Format the questions for display in a multiselect widget.
                # (We remove any bold Markdown markers for the selection options.)
                options = [question.strip().replace('**', '') for question, _ in qa_pairs]
                
                # Allow multiple questions to be selected.
                selected_question = st.multiselect(
                    "Question(s) sauvegardée(s)",
                    options,
                    key="multi_qna"
                )
                
                # Button to save the selected questions, with a unique key.
                if st.button("Sauvegarder la sélection", key="save_selected_qna"):
                    if selected_question:
                        # Build the file path to save the questions.
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
    # Define few variables
    file_name = re.sub(r"\.pdf$", "", uploaded_file.name)
    input_file_path = os.path.join(input_folder, uploaded_file.name)
    output_file_path_pdf = os.path.join(output_folder, file_name, file_name + ".pdf")
    output_file_path_txt = os.path.join(output_folder, file_name, file_name + "_Combine.txt")
    summary_file_name = os.path.join(output_folder, file_name, f"{file_name}_Resume.txt")
    summary_content = read_text_file(summary_file_name)
    questions_txt_path = os.path.join(output_folder, "Questions_Saved.txt")
    qna_file_name = os.path.join(output_folder, file_name, f"{file_name}_Q&A_Saved.txt")
    
    # Check if the file (or folder) already exists in output_folder or its subfolders
    file_exists = False
    for root, dirs, files in os.walk(output_folder):
        if file_name in dirs or file_name in files:
            file_exists = True
            break

    try:
        image_paths = pdf_to_images(input_folder, uploaded_file.name, output_folder)
        nb_images = len(image_paths)

        ########################################
        # Step 1: Upload and save the PDF
        ########################################

        save_uploaded_file(uploaded_file, input_file_path, output_file_path_pdf)

        ########################################
        # Step 2: Process the PDF for OCR and Download .txt files
        ########################################
        
        if not file_exists:

            # Process the PDF for OCR
            with st.spinner("Traitement OCR du PDF..."):
                pdf_to_ocr(input_file_path, output_folder)

            # Download .txt files (wait time based on the number of images)
            nb_secondes = 10 * nb_images
            time.sleep(nb_secondes)
            with st.spinner(f"Téléchargement des {nb_images} fichiers .txt ({nb_secondes}s)..."):
                ocr_list_download_combine_txt_file()
        
        ########################################
        # Step 3: Display Expanders
        ########################################
        
        with st.spinner("Image..."):
            display_images()
        with st.spinner("Résumé..."):
            display_resume()
        with st.spinner("Q&A..."):
            display_qna_saved()
        with st.spinner("Q&A Suggestion..."):
            display_qna_suggestions()

        ########################################
        # Step 4: GPT Interaction
        ########################################

        # Initialize the session state variable if it doesn't exist
        if "generated_answer" not in st.session_state:
            st.session_state.generated_answer = ""

        sys_prompt = "Vous êtes un arpenteur et notaire d'experience. Je suis un client."
        question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
        assistant_answer = f"Oui, voici le contenu du document : {summary_content}"
        user_prompt = st.text_area("Je suis expert notaire et arpenteur-géomètre", placeholder="Posez moi votre question...")

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
        st.markdown("### Réponse Générée")
        st.write(st.session_state.generated_answer)

    except Exception as e:
        st.error("Une erreur s'est produite lors du traitement du PDF.")
        st.exception(e)


########################################
# GPT Interaction
########################################

# # Initialize the session state variable if it doesn't exist
# if "generated_answer" not in st.session_state:
#     st.session_state.generated_answer = ""

# sys_prompt = "Vous êtes un arpenteur et notaire d'experience. Je suis un client."
# question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
# assistant_answer = f"Oui, voici le contenu du document : {summary_content}"
# user_prompt = st.text_area("Je suis expert notaire et arpenteur-géomètre", placeholder="Posez moi votre question...")

# # Button to generate the response
# if st.button("Générer la réponse"):
#     generated_answer = gpt_prompt(sys_prompt, question_prompt, assistant_answer, user_prompt, None)
#     st.session_state.generated_answer = generated_answer

# # Button to save the question (and/or response if they exist)
# if st.session_state.generated_answer or user_prompt:
#     if st.button("Enregistrer la question"):
#         answer_file_path = os.path.join(output_folder, "Questions_Saved.txt")
#         try:
#             save_to_txt(user_prompt, answer_file_path, operation="insert")
#         except Exception as e:
#             st.error(f"Erreur lors de l'enregistrement : {e}")

# # Always display the generated answer if it exists
# st.markdown("### Réponse Générée")
# st.write(st.session_state.generated_answer)



