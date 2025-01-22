import os
import logging
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

def txt_file_to_gpt(txt_file_path, sys_prompt, user_prompt):
    """
    Lit un fichier texte et interagit avec GPT pour générer une réponse basée sur les prompts donnés.

    Args:
        txt_file_path (str): Chemin du fichier texte.
        sys_prompt (str): Prompt système pour orienter le modèle.
        user_prompt (str): Prompt utilisateur pour orienter la réponse.

    Returns:
        dict: Contenant les données de la complétion ou un message d'erreur.
    """
    # Lire le contenu du fichier texte
    try:
        with open(txt_file_path, 'r', encoding='utf-8') as file:
            txt_file_content = file.read()
    except FileNotFoundError:
        return {"error": "Le fichier spécifié est introuvable."}
    except Exception as e:
        return {"error": f"Une erreur s'est produite : {str(e)}"}

    # Initialiser l'historique des messages
    message_history = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": "Je vous ai envoyé un document, l'avez-vous reçu?"},
        {"role": "assistant", "content": f"Oui, voici le contenu du document : {txt_file_content}"},
        {"role": "user", "content": user_prompt}
    ]

    # Appeler l'API de complétion
    try:
        completion = client.chat.completions.create(
            model=gpt_model,
            messages=message_history,
        )

        # Extraire les données de la réponse
        gen_answ_data = {
            "sys_prompt": sys_prompt,
            "question_prompt": "Je vous ai envoyé un document, l'avez-vous reçu?",
            "assistant_answer": f"Oui, voici le contenu du document : {txt_file_content}",
            "user_prompt": user_prompt,
            "gen_answ_id": completion.id,
            "gen_answ_content": completion.choices[0].message.content,
            "gen_answ_role": completion.choices[0].message.role,
            "gen_answ_created": completion.created,
            "gen_answ_model": completion.model,
            "gen_answ_completion_tokens": completion.usage.completion_tokens,
            "gen_answ_prompt_tokens": completion.usage.prompt_tokens,
            "gen_answ_total_tokens": completion.usage.total_tokens
        }
        return gen_answ_data

    except Exception as e:
        return {"error": f"Une erreur s'est produite lors de l'appel à l'API : {str(e)}"}

if __name__ == "__main__":
    # Exemple d'utilisation
    # txt_file = "C:/Users/Guillaume.Cote/Documents/GitHub_Arpenteur/Document du Registre Foncier PNG_/AL_37_20_158_RB_pdf/AL_37_20_158_RB_pdf_Combine.txt"
    txt_file = "Document_du_Registre_Foncier_PNG/AL_37_177_327_pdf/AL_37_177_327_pdf_Combine.txt"

    sys_prompt = "Tu es un notaire/arpenteur et je suis un client."
    user_prompt = "Parlez-moi de ce document, s'il vous plaît. Soyez précis."

    completions_data = txt_file_to_gpt(txt_file, sys_prompt, user_prompt)

    if "error" in completions_data:
        logging.error(completions_data["error"])
    else:
        logging.info("Réponse générée avec succès :")
        logging.info(completions_data)
