import streamlit as st
import os
from Arpenteur_Step3_GPT import txt_file_to_gpt

# Titre de l'application
st.title("PDF Analysis Using GPT")

# Instructions
st.markdown("""
Téléchargez un fichier texte, définissez les prompts et recevez une analyse générée par GPT.
""")

# Téléchargement du fichier
uploaded_file = st.file_uploader("Téléchargez votre fichier texte ici", type=["txt"])

# Champs pour les prompts
# sys_prompt = st.text_area("Prompt système", "Tu es un notaire/arpenteur et je suis un client.")
user_prompt = st.text_area("Prompt utilisateur", "Parlez-moi de ce document, s'il vous plaît. Soyez précis.")

# Bouton pour lancer l'analyse
if st.button("Analyser le document"):
    if uploaded_file is not None:
        try:
            with st.spinner("Traitement en cours..."):
                # Sauvegarder le fichier temporairement
                temp_file_path = os.path.join("temp_uploaded_file.txt")
                output_csv_file = os.path.join("temp_output_data.csv")
                with open(temp_file_path, "w", encoding="utf-8") as temp_file:
                    temp_file.write(uploaded_file.getvalue().decode("utf-8"))

                # Appeler la fonction d'analyse
                # completions_data = txt_file_to_gpt(temp_file_path, sys_prompt, user_prompt, output_csv_file)
                completions_data = txt_file_to_gpt(temp_file_path, user_prompt, output_csv_file)

                # Supprimer les fichiers temporaires
                os.remove(temp_file_path)
                if os.path.exists(output_csv_file):
                    os.remove(output_csv_file)

            # Afficher les résultats
            if "error" in completions_data:
                st.error(f"Erreur : {completions_data['error']}")
            else:
                st.success("Analyse réussie ! Voici les résultats :")
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
        st.warning("Veuillez télécharger un fichier avant de lancer l'analyse.")
