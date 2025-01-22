import os
import logging
import csv
from openai import OpenAI
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configurer le client OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
gpt_model = "gpt-4o-mini"

# Configurer le journal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def txt_file_to_gpt(txt_file_path, sys_prompt, user_prompt, output_csv_file):
    """
    Lit un fichier texte, interagit avec GPT pour générer une réponse, et enregistre directement dans un fichier CSV.

    Args:
        txt_file_path (str): Chemin du fichier texte.
        sys_prompt (str): Prompt système pour orienter le modèle.
        user_prompt (str): Prompt utilisateur pour orienter la réponse.
        output_csv_file (str): Chemin du fichier CSV où enregistrer les résultats.

    Returns:
        str: Contenu généré par GPT.
    """
    # Lire le contenu du fichier texte
    try:
        with open(txt_file_path, 'r', encoding='utf-8') as file:
            txt_file_content = file.read()
    except FileNotFoundError:
        logging.error("Le fichier spécifié est introuvable.")
        return "Le fichier spécifié est introuvable."
    except Exception as e:
        logging.error(f"Une erreur s'est produite : {str(e)}")
        return f"Une erreur s'est produite : {str(e)}"

    question_prompt = "Je vous ai envoyé un document, l'avez-vous reçu?"
    assistant_answer = f"Oui, voici le contenu du document : {txt_file_content}"

    # Initialiser l'historique des messages
    message_history = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": question_prompt},
        {"role": "assistant", "content": assistant_answer},
        {"role": "user", "content": user_prompt}
    ]

    # Appeler l'API de complétion
    try:
        completion = client.chat.completions.create(
            model=gpt_model,
            messages=message_history,
        )

        # Extraire les données de la réponse
        gen_answ_content = completion.choices[0].message.content
        gen_answ_data = {
            "txt_file_path": txt_file_path,
            "sys_prompt": sys_prompt,
            "question_prompt": question_prompt,
            "assistant_answer": assistant_answer,
            "user_prompt": user_prompt,
            "gen_answ_id": completion.id,
            "gen_answ_content": gen_answ_content,
            "gen_answ_role": completion.choices[0].message.role,
            "gen_answ_created": completion.created,
            "gen_answ_model": completion.model,
            "gen_answ_completion_tokens": completion.usage.completion_tokens,
            "gen_answ_prompt_tokens": completion.usage.prompt_tokens,
            "gen_answ_total_tokens": completion.usage.total_tokens
        }

        # Enregistrer dans un fichier CSV
        try:
            with open(output_csv_file, mode='w', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(gen_answ_data.keys())  # En-têtes
                writer.writerow(gen_answ_data.values())  # Valeurs

            logging.info(f"Données enregistrées avec succès dans {output_csv_file}.")
        except Exception as e:
            logging.error(f"Une erreur s'est produite lors de l'enregistrement du fichier CSV : {str(e)}")

        return gen_answ_content

    except Exception as e:
        logging.error(f"Une erreur s'est produite lors de l'appel à l'API : {str(e)}")
        return f"Une erreur s'est produite lors de l'appel à l'API : {str(e)}"

def txt_file_to_gpt_batch(txt_file_path, sys_prompt, user_prompts, output_csv_file):
    """
    Gère une liste de prompts utilisateur et génère des réponses pour chacun.

    Args:
        txt_file_path (str): Chemin du fichier texte.
        sys_prompt (str): Prompt système pour orienter le modèle.
        user_prompts (list): Liste des prompts utilisateur.
        output_csv_file (str): Chemin du fichier CSV où enregistrer les résultats.

    Returns:
        list: Liste des contenus générés par GPT pour chaque prompt.
    """
    all_responses = []

    # Créer un fichier CSV avec les en-têtes au préalable
    try:
        with open(output_csv_file, mode='w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            headers = [
                "txt_file_path", "sys_prompt", "question_prompt",
                "assistant_answer", "user_prompt", "gen_answ_id",
                "gen_answ_content", "gen_answ_role", "gen_answ_created",
                "gen_answ_model", "gen_answ_completion_tokens",
                "gen_answ_prompt_tokens", "gen_answ_total_tokens"
            ]
            writer.writerow(headers)

    except Exception as e:
        logging.error(f"Erreur lors de la création du fichier CSV : {str(e)}")
        return []

    # Traiter chaque prompt utilisateur
    for user_prompt in user_prompts:
        response = txt_file_to_gpt(txt_file_path, sys_prompt, user_prompt, output_csv_file)
        all_responses.append(response)

        # Ajouter les données pour ce prompt dans le fichier CSV
        try:
            with open(output_csv_file, mode='a', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)

                # Extraire les données supplémentaires pour chaque prompt
                writer.writerow([
                    txt_file_path, sys_prompt, "Je vous ai envoyé un document, l'avez-vous reçu?",
                    f"Oui, voici le contenu du document : {open(txt_file_path, 'r', encoding='utf-8').read()}",
                    user_prompt, "N/A", response, "N/A", "N/A", gpt_model,
                    "N/A", "N/A", "N/A"
                ])

        except Exception as e:
            logging.error(f"Erreur lors de l'enregistrement des données dans le CSV : {str(e)}")

    return all_responses

if __name__ == "__main__":
    # Exemple d'utilisation avec une liste de prompts
    txt_file = "Document_du_Registre_Foncier_PNG/AL_37_177_327_pdf/AL_37_177_327_pdf_Combine.txt"
    sys_prompt = "Tu es un notaire/arpenteur et je suis un client."
    user_prompts = [
        "Parlez-moi de ce document, s'il vous plaît. Soyez précis.",
        "Si existante, quelle est la date de droit du registre?",
        "Si existante, quelle est la circonscription?",
        "Si existante, quel est le cadastre?",
        "Si existante, quelle est la date d’établissement?",
        "Si existante, quelle est la concordance ?",
        "Pouvez-vous me donner un résumé clair et concis?"
    ]
    output_csv_file = "completions_data_batch.csv"

    gen_contents = txt_file_to_gpt_batch(txt_file, sys_prompt, user_prompts, output_csv_file)
    print("Contenus générés par GPT pour chaque prompt :", gen_contents)
