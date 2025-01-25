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
st.set_page_config(page_title="Title", layout="wide")

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

# # File upload section
# uploaded_file = st.file_uploader("Téléchargez un fichier PDF", type=["pdf"])

# if uploaded_file:
#     pdf_path = os.path.join(input_folder, uploaded_file.name)
#     if not os.path.exists(pdf_path):
#         with open(pdf_path, "wb") as f:
#             f.write(uploaded_file.getbuffer())

#     with st.spinner("Téléchargement en cours..."):
#         try:
#             # # Step 1: Process PDFs
#             # process_pdfs(input_folder, output_folder)

#             # Step 2: List and download documents
#             documents = list_documents()

#             if not documents:
#                 st.warning("Aucun document trouvé ou erreur lors de la récupération des documents.")
#             else:
#                 for document in documents:
#                     document_id = document.get("document_id")
#                     file_page_name = document.get("original_file_name", "document")
#                     file_name = re.sub(r"__.+", "", file_page_name)

#                     if document_id:
#                         download_document(document_id, file_name)

#             # Step 3: Combine text files
#             combine_page_files(output_folder)
#             st.success(f"{file_name}.pdf a été téléchargé avec succès!")

#         except Exception as e:
#             st.error("Une erreur s'est produite lors du traitement, du téléchargement ou de la combinaison des fichiers.")
#             st.exception(e)

########################################
# PDF Analysis
########################################

# Get a list of combined .txt files from subfolders in the output folder
file_list = get_combine_txt_files_in_subfolders(output_folder)
# Simplify file names for display in the selection box
file_list_display = [re.sub(r"(.+\/|_Combine\.txt)", "", f) for f in file_list]

st.markdown("### Analyse des fichiers TXT combinés")
# Dropdown for users to select a file from the list
# Sort the file list in ascending order
file_list_display_sorted = sorted(file_list_display)

# Display the sorted list in the selectbox
selected_file_display = st.selectbox("Sélectionnez un fichier :", file_list_display_sorted)


if selected_file_display:
    # Get the index of the selected file
    selected_file_index = file_list_display.index(selected_file_display)
    # Retrieve the corresponding full file path
    selected_file = file_list[selected_file_index]
else:
    selected_file = None

# Expandable section to view associated images
with st.expander("Voir les images associées au PDF", expanded=False):
    # Choose the number of columns to display images
    num_columns = st.radio("Nombre de colonnes pour afficher les images :", options=[1,5], index=1)

    if selected_file:
        # Get associated PNG files in the same folder as the selected file
        png_files = get_png_files_in_same_folder(selected_file)

        if png_files:
            for i in range(0, len(png_files), num_columns):
                # Create the chosen number of columns for image display
                cols = st.columns(num_columns)
                for col, png_file in zip(cols, png_files[i:i + num_columns]):
                    with col:
                        st.image(png_file, caption=os.path.basename(png_file), use_container_width=True)  # Display each image with its file name
        else:
            st.info("Aucune image .png trouvée dans le même dossier que le fichier sélectionné.")  # Inform the user if no PNG files are found


# Prompt and analysis section
sys_prompt = "Tu es un notaire/arpenteur et je suis un client."
user_prompt = st.text_area("Prompt utilisateur", "Parlez-moi de ce document, s'il vous plaît. Soyez précis.")

# Button to trigger document analysis
if st.button("Analyser le document"):
    # Ensure a valid file is selected and exists
    if selected_file and os.path.exists(selected_file):
        try:
            # Display a spinner during processing
            with st.spinner("Analyse en cours..."):
                # Generate a timestamp
                timestamp = datetime.now(pytz.timezone('America/Montreal')).strftime("%Y%m%d_%Hh%M")

                # Extract base name from the file
                file_name = re.sub(r".+\/|_Combine|\.txt", "", selected_file)
                # Create a unique output file name
                output_csv_file_name = f"{file_name}_{timestamp}.csv"

                # Remove existing output file if it exists
                if os.path.exists(output_csv_file_name):
                    os.remove(output_csv_file_name)

                # Call the GPT processing function
                completions_data = txt_file_to_gpt(selected_file, sys_prompt, user_prompt, output_csv_file_name)

            if "error" in completions_data:
                # Display an error message if processing failed
                st.error(f"Erreur : {completions_data['error']}")
            else:
                if isinstance(completions_data, str):
                    # Display results in a text area if they are a string
                    st.text_area("Résultats de l'analyse", completions_data, height=300)
                elif isinstance(completions_data, dict):
                    # Display results as JSON if they are a dictionary
                    st.json(completions_data)
                else:
                    # Display results in a general format
                    st.write(completions_data)

        except Exception as e:
            # Display any exception that occurs during processing
            st.error(f"Une erreur s'est produite : {str(e)}")
    else:
        # Warn the user if no valid file is selected
        st.warning("Veuillez sélectionner un fichier valide avant de lancer l'analyse.")
