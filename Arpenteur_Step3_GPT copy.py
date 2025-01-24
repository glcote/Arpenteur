import logging
from dotenv import load_dotenv
from Utils import txt_file_to_gpt, txt_file_to_gpt_batch

# Charger les variables d'environnement
load_dotenv()

# Configurer le journal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


if __name__ == "__main__":
    # Exemple d'utilisation avec une liste de prompts
    txt_file_path = "Document_du_Registre_Foncier_PNG/AL_37_177_327_pdf/AL_37_177_327_pdf_Combine.txt"
    sys_prompt = "Tu es un notaire/arpenteur et je suis un client."
    user_prompt = """Parlez-moi de ce document, s'il vous plaît. Soyez précis.
        Si existante, quelle est la date de droit du registre?
        Si existante, quelle est la circonscription?
        Si existant, quel est le cadastre?
        Si existante, quelle est la date d’établissement?
        Si existante, quelle est la concordance ?"""

    gen_content = txt_file_to_gpt(txt_file_path, sys_prompt, user_prompt)
    print("Contenus générés par GPT pour chaque prompt :", gen_content)

# if __name__ == "__main__":
#     # Exemple d'utilisation avec une liste de prompts
#     txt_file = "Document_du_Registre_Foncier_PNG/AL_37_177_327_pdf/AL_37_177_327_pdf_Combine.txt"
#     sys_prompt = "Tu es un notaire/arpenteur et je suis un client."
#     user_prompts = [
#         """Parlez-moi de ce document, s'il vous plaît. Soyez précis.
#         Si existante, quelle est la date de droit du registre?
#         Si existante, quelle est la circonscription?
#         Si existant, quel est le cadastre?
#         Si existante, quelle est la date d’établissement?
#         Si existante, quelle est la concordance ?"""

#         # "Parlez-moi de ce document, s'il vous plaît. Soyez précis.",
#         # "Si existante, quelle est la date de droit du registre?",
#         # "Si existante, quelle est la circonscription?",
#         # "Si existant, quel est le cadastre?",
#         # "Si existante, quelle est la date d’établissement?",
#         # "Si existante, quelle est la concordance ?"
#     ]
#     output_csv_file = "completions_data_batch.csv"

#     gen_contents = txt_file_to_gpt_batch(txt_file, sys_prompt, user_prompts, output_csv_file)
#     print("Contenus générés par GPT pour chaque prompt :", gen_contents)
