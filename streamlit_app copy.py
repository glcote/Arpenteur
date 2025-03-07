import os
import re
import time
import logging
import base64
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

# NOT USE - Define your helper function to display images
def display_images(uploaded_file, nb_images, image_paths):
    """
    Display images extracted from a PDF file in a Streamlit app.
    
    Parameters:
        uploaded_file: The file object uploaded by the user.
        nb_images: The number of pages/images generated from the PDF.
        image_paths: A list of paths to the generated images.
    """
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

def display_pdf(uploaded_file):
    """
    Display the PDF file in an embedded viewer, allowing clickable links.
    
    Parameters:
        uploaded_file: The file object (PDF) uploaded by the user.
    """
    try:
        # Add a Markdown link to "Voir OCR"
        st.markdown("[Voir OCR](https://www.handwritingocr.com/dashboard)", unsafe_allow_html=True)
        
        # Create an expander with the file name
        with st.expander(uploaded_file.name):
            # Ensure we're reading from the start of the file
            uploaded_file.seek(0)
            
            # Convert PDF file to base64
            base64_pdf = base64.b64encode(uploaded_file.read()).decode('utf-8')
            pdf_display = f'''
                <iframe 
                    src="data:application/pdf;base64,{base64_pdf}"
                    width="100%" 
                    height="1024px"
                    type="application/pdf">
                </iframe>
            '''
            st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.error("Une erreur s'est produite lors de l'affichage du PDF.")
        logging.error(f"Erreur lors de l'affichage du PDF : {e}")

def display_resume(output_file_path_txt, summary_file_name):
    """
    Generate and display a summary from the given text file content.
    
    Parameters:
        output_file_path_txt (str): The path to the text file containing the document content.
        output_folder (str): The folder where the summary file will be stored.
        file_name (str): The base file name (without extension) used to build the summary file path.
    """
    try:
        # Add a button to refresh the summary
        refresh = st.button("Rafraîchir", key="refresh_resume")

        # Define variables for GPT
        file_content = read_text_file(output_file_path_txt)
        sys_prompt = "Vous êtes un arpenteur et notaire d'experience. Je suis un client."
        question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
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

def display_qna_saved(questions_txt_path, summary_file_name, qna_file_name):
    """
    Display Q&A responses for every saved questions using GPT.
    
    The function checks for a saved Q&A file in the output_folder. If the file does not exist 
    or if the user clicks "Refresh" button, it regenerates the responses, saves them, 
    and then displays the results.
    
    Assumes the existence of:
        - questions_txt_path: path to the saved questions (one per line).
        - summary_file_name: path to the summary file used as context.
    """
    # Create an expander for Q&A content
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

def display_qna_suggestions(output_folder, file_name, summary_file_name):
    """
    Generate and display Q&A suggestions based on a document summary,
    allow the user to select questions, and save them.

    Assumes the existence of:
        - output_folder: folder where output files are stored.
        - file_name: base name of the file (without extension).
        - summary_file_name: path to the summary file.
    """
    st.info("Voici quelques suggestions de questions/réponses que vous pouvez ensuite sauvegarder.")
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
Veuillez mettre les questions en **gras** svp."""
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
        
        # For display purposes, remove the "Q:" and "A:" markers from the raw text
        gen_answer_display = gen_answer.replace("Q: ", "").replace("A: ", "")
        st.markdown(gen_answer_display)
        
        # ----------------------------------------------
        # Extraction of Q&A pairs from the generated text
        # ----------------------------------------------
        qa_pairs = re.findall(
            r"Q\s?:\s*(.*?)\s*A\s?:\s*(.*?)(?=\nQ\s?:|\Z)",
            gen_answer,
            re.DOTALL
        )
        # Fallback if no pairs are found
        if not qa_pairs:
            parts = gen_answer.split("\n\n")
            if parts:
                main_question = parts[0].strip()
                remaining_text = "\n\n".join(parts[1:]).strip()
                qa_pairs = [(main_question, remaining_text)]
        
        # Display the extracted Q&A pairs
        if qa_pairs:
            qna_responses = ""
            for question, answer in qa_pairs:
                clean_question = question.strip().rstrip('*').strip()
                qna_responses += f"**{clean_question}**\n\n{answer.strip()}\n\n"
            # st.markdown(qna_responses)
            
            # ----------------------------------------------------
            # Extract ALL questions (including nested ones) into an options list for saving
            # ----------------------------------------------------
            st.markdown("--------")
            st.info("Vous pouvez sauvegarder une question et mettre à jour ou supprimer une question sauvegardée.")
            
            options = []
            for main_question, content in qa_pairs:
                # Add the main question (first element of the tuple)
                clean_main_question = main_question.strip().rstrip('*').strip()
                options.append(clean_main_question)
                # Now extract any nested questions from the content (if they exist)
                nested_questions = re.findall(r"Q\s?:\s*(.*?)\s*A\s?:", content)
                for nq in nested_questions:
                    clean_nq = nq.strip().rstrip('*').strip()
                    options.append(clean_nq)
            
            # Remove any duplicate questions
            options = list(dict.fromkeys(options))
            
            # Let the user select which questions to save
            selected_questions = st.multiselect("Sélectionnez les questions à sauvegarder", options, key="multi_qna")
            if st.button("Sauvegarder", key="save_selected_qna"):
                if selected_questions:
                    # Build the file path to save the questions.
                    question_file_name = os.path.join(output_folder, "Questions_Saved.txt")
                    save_to_txt(selected_questions, question_file_name, operation="insert")
                    st.success("Les questions ont été sauvegardées !")
                else:
                    st.warning("Veuillez sélectionner au moins une question avant de sauvegarder.")
        else:
            st.warning("Aucune question n'a pu être extraite du texte généré.")
        
        # ----------------------------------------------
        # Manage Saved Questions: Update and Delete
        # ----------------------------------------------
        saved_questions_file = os.path.join(output_folder, "Questions_Saved.txt")
        if os.path.exists(saved_questions_file):
            # Read saved questions from file; assuming one question per line
            with open(saved_questions_file, "r", encoding="utf-8") as f:
                saved_questions = [line.strip() for line in f if line.strip()]
        else:
            saved_questions = []
        
        if saved_questions:
            selected_saved_question = st.selectbox("Sélectionnez une question", saved_questions, key="saved_question_select")
            new_question_text = st.text_input("Modifier la question", value=selected_saved_question, key="update_question_input")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Mettre à jour la question", key="update_question_button"):
                    try:
                        # Update the selected question in the list
                        index = saved_questions.index(selected_saved_question)
                        saved_questions[index] = new_question_text
                        # Write the updated list back to the file
                        with open(saved_questions_file, "w", encoding="utf-8") as f:
                            for q in saved_questions:
                                f.write(q + "\n")
                        st.success("La question a été mise à jour.")
                    except Exception as update_error:
                        st.error(f"Erreur lors de la mise à jour : {update_error}")
            with col2:
                if st.button("Supprimer la question", key="delete_question_button"):
                    try:
                        # Remove the selected question from the list
                        saved_questions.remove(selected_saved_question)
                        # Write the updated list back to the file
                        with open(saved_questions_file, "w", encoding="utf-8") as f:
                            for q in saved_questions:
                                f.write(q + "\n")
                        st.success("La question a été supprimée.")
                    except Exception as delete_error:
                        st.error(f"Erreur lors de la suppression : {delete_error}")
        else:
            st.warning("Aucune question sauvegardée à gérer.")
                
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
        ########################################
        # Step 1: Upload and save the PDF
        ########################################

        save_uploaded_file(uploaded_file, input_file_path, output_file_path_pdf)
        image_paths = pdf_to_images(input_folder, uploaded_file.name, output_folder)
        nb_images = len(image_paths)


        ########################################
        # Step 2: Process the PDF for OCR and Download .txt files
        ########################################

        if not file_exists:

            # Process the PDF for OCR
            with st.spinner("Traitement OCR du PDF..."):
                # pdf_to_ocr(input_file_path, output_folder)
                pdf_to_ocr(input_folder, output_folder)            
            
            # Wait until all .txt files are processed and ready for download
            expected_txt_count = nb_images  # assuming one .txt file per image
            timeout = 20  # maximum wait time in seconds
            poll_interval = 5  # seconds between checks

            with st.spinner("Traitement OCR..."):
                start_time = time.time()
                while True:
                    # For example, if the OCR API saves the .txt files in a known output folder:
                    txt_files = [
                        f for f in os.listdir(output_folder)
                        if f.endswith(".txt") and file_name in f  # assuming file_name is in the .txt file names
                    ]
                    if len(txt_files) >= expected_txt_count:
                        break  # All files are ready
                    if time.time() - start_time > timeout:
                        st.error("Le traitement OCR a pris trop de temps.")
                        break
                    time.sleep(poll_interval)

            with st.spinner("Téléchargement des fichiers .txt en cours..."):
                ocr_list_download_combine_txt_file()

        else:
            # Delete the PDF file from the input folder since it already exists in output_folder
            try:
                os.remove(input_file_path)
                logging.info(f"PDF file deleted from: {input_file_path}")
            except Exception as e:
                st.error("Erreur lors de la suppression du fichier PDF existant.")
                logging.error(f"Erreur lors de la suppression du fichier PDF: {e}")
        
        ########################################
        # Step 3: Display Expanders
        ########################################

        with st.spinner("PDF..."):
            with st.spinner("PDF en cours..."):
                display_pdf(uploaded_file)

        with st.spinner("PDF with OCR..."):
            with st.spinner("PDF with OCR en cours..."):
                display_pdf_with_ocr(uploaded_file)

        with st.spinner("Résumé..."):
            with st.expander("Résumé"):
                display_resume(output_file_path_txt, summary_file_name)

        # Only display the Q&A section if the Q&A file exists
        if os.path.exists(questions_txt_path):
            with st.spinner("Q&A Saved..."):
                with st.expander("Q&A Saved"):
                    display_qna_saved(questions_txt_path, summary_file_name, qna_file_name)

        with st.spinner("Q&A Suggestion..."):
            with st.expander("Q&A Suggestion"):
                display_qna_suggestions(output_folder, file_name, summary_file_name)

        # ########################################
        # # Step 4: GPT Interaction
        # ########################################

        # # Initialize the session state variable if it doesn't exist
        # if "generated_answer" not in st.session_state:
        #     st.session_state.generated_answer = ""

        # sys_prompt = "Vous êtes un arpenteur et notaire d'experience. Je suis un client."
        # question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
        # assistant_answer = f"Oui, voici le contenu du document : {output_file_path_txt}"
        # user_prompt = st.text_area("Je suis expert notaire et arpenteur-géomètre", placeholder="Posez moi votre question...")

        # st.markdown(assistant_answer)

        # # Button to generate the response
        # if st.button("Générer la réponse"):
        #     generated_answer = gpt_prompt(sys_prompt, question_prompt, assistant_answer, user_prompt, None)
        #     st.session_state.generated_answer = generated_answer

        # # # Button to save the question (and/or response if they exist)
        # # if st.session_state.generated_answer or user_prompt:
        # #     if st.button("Enregistrer la question"):
        # #         answer_file_path = os.path.join(output_folder, "Questions_Saved.txt")
        # #         try:
        # #             save_to_txt(user_prompt, answer_file_path, operation="insert")
        # #         except Exception as e:
        # #             st.error(f"Erreur lors de l'enregistrement : {e}")
        # #     st.markdown("### Réponse Générée")

        # # # Always display the generated answer if it exists
        # # st.markdown("### Réponse Générée")
        # st.write(st.session_state.generated_answer)

    except Exception as e:
        st.error("Une erreur s'est produite lors du traitement du PDF.")
        st.exception(e)
