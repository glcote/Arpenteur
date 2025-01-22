import streamlit as st
import os
import re
from Utils import get_combine_txt_files_in_subfolders, get_png_files_in_same_folder
from Arpenteur_Step3_GPT import txt_file_to_gpt

# Définir le chemin du dossier contenant les fichiers
folder_path = "Document_du_Registre_Foncier_PNG"

# Récupérer la liste des fichiers filtrés
file_list = get_combine_txt_files_in_subfolders(folder_path)

# Créer une liste pour l'affichage simplifié des noms
file_list_display = [re.sub(r"(.+\/|_Combine\.txt)", "", f) for f in file_list]

# Titre de l'application
st.title("PDF Analysis Using GPT")

# Instructions
st.markdown("""
Sélectionnez un fichier, définissez votre prompt et recevez une analyse générée par GPT.
""")

# Option de sélection de fichier depuis le dossier
selected_file_display = st.selectbox("Sélectionnez un fichier :", file_list_display)

# Récupérer le chemin complet du fichier sélectionné en fonction de son nom affiché
if selected_file_display:
    selected_file_index = file_list_display.index(selected_file_display)
    selected_file = file_list[selected_file_index]
else:
    selected_file = None

with st.expander("Voir le PDF", expanded=False):
    # Option pour sélectionner le nombre de colonnes
    num_columns = st.radio("Nombre de colonnes pour afficher les images :", options=[1, 5], index=1)

    # Si un fichier est sélectionné, récupérer les fichiers PNG associés
    if selected_file:
        png_files = get_png_files_in_same_folder(selected_file)

        # Afficher les images PNG triées par numéro de page
        if png_files:
            # Diviser les images en groupes selon le nombre de colonnes sélectionné
            for i in range(0, len(png_files), num_columns):
                cols = st.columns(num_columns)  # Créer le nombre de colonnes sélectionné
                for col, png_file in zip(cols, png_files[i:i + num_columns]):
                    with col:
                        st.image(png_file, caption=os.path.basename(png_file), use_container_width=True)
        else:
            st.info("Aucune image .png trouvée dans le même dossier que le fichier sélectionné.")

# Champs pour les prompts
sys_prompt = "Tu es un notaire/arpenteur et je suis un client."
user_prompt = st.text_area("Prompt utilisateur", "Parlez-moi de ce document, s'il vous plaît. Soyez précis.")

# Ajout de la nouvelle section visuelle avec des boutons
st.markdown("### Choisissez une option :")
options = ["Résumé", "Exemple", "Autre"]

# Utilisation de colonnes pour afficher les options comme des boutons
cols = st.columns(len(options))
selected_option = None

# Gestion des boutons pour sélectionner une option
for i, option in enumerate(options):
    if cols[i].button(option):
        selected_option = option

# Afficher la sélection pour confirmation (facultatif)
if selected_option:
    st.write(f"Option sélectionnée : **{selected_option}**")

# Bouton pour lancer l'analyse
if st.button("Analyser le document"):
    if selected_file and os.path.exists(selected_file):
        try:
            with st.spinner("Traitement en cours..."):
                # Appeler la fonction d'analyse
                output_csv_file = os.path.join("temp_output_data.csv")
                completions_data = txt_file_to_gpt(selected_file, sys_prompt, user_prompt, output_csv_file)

                # Supprimer le fichier temporaire CSV si nécessaire
                if os.path.exists(output_csv_file):
                    os.remove(output_csv_file)

            # Afficher les résultats
            if "error" in completions_data:
                st.error(f"Erreur : {completions_data['error']}")
            else:
                # Vérifier si les résultats sont longs et choisir l'affichage adapté
                if isinstance(completions_data, str):
                    st.text_area("Résultats de l'analyse", completions_data, height=300)
                elif isinstance(completions_data, dict):
                    st.json(completions_data)
                else:
                    st.write(completions_data)

        except Exception as e:
            st.error(f"Une erreur s'est produite : {str(e)}")
    else:
        st.warning("Veuillez sélectionner un fichier valide avant de lancer l'analyse.")
