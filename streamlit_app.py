import streamlit as st
import os
from Arpenteur_Step3_GPT import txt_file_to_gpt

# Titre de l'application
st.title("Application d'Analyse Documentaire avec GPT")

# Instructions
st.markdown("""
Téléchargez un fichier texte, définissez les prompts et recevez une analyse générée par GPT.
""")

# Téléchargement du fichier
uploaded_file = st.file_uploader("Téléchargez votre fichier texte ici", type=["txt"])

# Champs pour les prompts
sys_prompt = st.text_area("Prompt système", "Tu es un notaire/arpenteur et je suis un client.")
user_prompt = st.text_area("Prompt utilisateur", "Parlez-moi de ce document, s'il vous plaît. Soyez précis.")

# Bouton pour lancer l'analyse
if st.button("Analyser le document"):
    if uploaded_file is not None:
        try:
            # Sauvegarder le fichier temporairement
            temp_file_path = os.path.join("temp_uploaded_file.txt")
            with open(temp_file_path, "w", encoding="utf-8") as temp_file:
                temp_file.write(uploaded_file.getvalue().decode("utf-8"))

            # Appeler la fonction d'analyse
            completions_data = txt_file_to_gpt(temp_file_path, sys_prompt, user_prompt)

            # Afficher les résultats
            if "error" in completions_data:
                st.error(f"Erreur : {completions_data['error']}")
            else:
                st.success("Analyse réussie ! Voici les résultats :")

                # Afficher les données générées
                st.json(completions_data)

            # Supprimer le fichier temporaire
            os.remove(temp_file_path)

        except Exception as e:
            st.error(f"Une erreur s'est produite : {str(e)}")
    else:
        st.warning("Veuillez télécharger un fichier avant de lancer l'analyse.")
