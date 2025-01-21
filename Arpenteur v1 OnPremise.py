import os
import re
import requests
from dotenv import load_dotenv 
from openai import OpenAI
import fitz #!pip install PyMuPDF
from PIL import Image

load_dotenv()

client = OpenAI(api_key = os.getenv("OPENAI_API_KEY"))
api_key_ocr_space = os.getenv("OCR_SPACE_API_KEY")
api_key_handwriting_ocr = os.getenv("API_KEY_HANDWRITING_OCR")
api_endpoint = "https://www.handwritingocr.com/api/v2/documents" #api_handwriting_ocr_endpoint

gpt_model = "gpt-4o-mini" # https://openai.com/api/pricing/

###################################

# Constants
input_folder = "Document du Registre Foncier"
output_folder = "Document du Registre Foncier PNG_"
# main_dir = f"C:/Users/Guillaume.Cote/Documents/GitHub_Arpenteur/{input_folder}"
# pdf_to_images_main_dir = f"{main_dir} PNG_"
output_format = "txt"  # Desired output format: txt, docx, xlsx, json

# Create input and output folders if they don't exist
os.makedirs(input_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

# Headers
headers = {
    "Authorization": f"Bearer {api_key_handwriting_ocr}",
    "Accept": "application/json",
}

###################################

# Fonction to convert a PDF to image per page
def pdf_to_images(folder_input_path, file_name, output_folder):
    pdf_file_path = os.path.join(folder_input_path, file_name)
    output_directory = os.path.join(output_folder, os.path.splitext(file_name)[0])
    os.makedirs(output_directory, exist_ok=True)

    doc = fitz.open(pdf_file_path)

    for page_num in range(len(doc)):
        try:
            # Charger la page
            page = doc.load_page(page_num)

            # Rendre la page en image
            pix = page.get_pixmap()

            # Convertir l'image en format PIL
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Sauvegarder l'image
            image_path = os.path.join(output_directory, f"{file_name}__page_{page_num + 1}.png")
            img.save(image_path)

        except Exception as e:
            print(f"Erreur lors du traitement de la page {page_num + 1}: {str(e)}")
            continue

    doc.close()
    return

# Boucle à travers les fichiers PDF du dossier
for file_name in os.listdir(input_folder):
    if file_name.endswith(".pdf"):
        print(f"Traitement de : {file_name}")
        pdf_to_images(
            folder_input_path=input_folder,
            file_name=file_name,
            output_folder=output_folder
        )

###################################

#############################################################
# ------------- COUTE 1 Credit (0.08$) par PAGE ------------- #
##############################################################

# Traiter toutes les pages ou uniquement certaines pages (ex. pages 1, 3 et 5)
def pdf_to_images(folder_input_path, file_name, output_folder, selected_pages=None):
    pdf_file_path = os.path.join(folder_input_path, file_name)
    output_directory = os.path.join(output_folder, os.path.splitext(file_name)[0])
    os.makedirs(output_directory, exist_ok=True)

    doc = fitz.open(pdf_file_path)
    
    pages_to_process = selected_pages if selected_pages is not None else range(len(doc))

    for page_num in pages_to_process:
        try:
            if page_num < 0 or page_num >= len(doc):
                print(f"Page {page_num + 1} hors des limites pour le fichier {file_name}")
                continue

            # Charger la page
            page = doc.load_page(page_num)

            # Rendre la page en image
            pix = page.get_pixmap()

            # Convertir l'image en format PIL
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Sauvegarder l'image
            image_path = os.path.join(output_directory, f"{file_name}__page_{page_num + 1}.png")
            img.save(image_path)

        except Exception as e:
            print(f"Erreur lors du traitement de la page {page_num + 1}: {str(e)}")
            continue

    doc.close()
    return output_directory

def transcribe_file(file_dir):
    """
    Upload a file to the Handwriting OCR API and transcribe it.
    :param file_dir: Path to the image file to transcribe.
    :return: Transcription result URL.
    """
    form_data = {
        "action": "transcribe",
        "delete_after": str(1209600), # Time in seconds (14 days)
    }

    with open(file_dir, "rb") as file:
        files = {"file": file}
        transcribe_response = requests.post(api_endpoint, headers=headers, data=form_data, files=files)
    return transcribe_response.json().get("result_url")

def process_pdfs(input_folder, output_folder, selected_pages):
    """
    Process all PDF files in a folder, converting them to images and transcribing the images.
    
    :param input_folder: Folder containing PDF files.
    :param output_folder: Folder to store the output images.
    :param selected_pages: List of pages to process or None for all pages.
    """
    os.makedirs(output_folder, exist_ok=True)

    for file_name in os.listdir(input_folder):
        if file_name.endswith(".pdf"):
            print(f"Traitement de : {file_name}")

            # Convert PDF to images
            image_folder = pdf_to_images(
                folder_input_path=input_folder,
                file_name=file_name,
                output_folder=output_folder,
                selected_pages=selected_pages
            )

            # Transcribe images
            for image_file in os.listdir(image_folder):
                if image_file.endswith(".png"):
                    image_path = os.path.join(image_folder, image_file)
                    print(f"Transcription de : {image_path}")

                    try:
                        result_url = transcribe_file(file_dir=image_path)
                        print(f"Résultat de la transcription pour {image_file} : {result_url}")
                    except Exception as e:
                        print(f"Erreur lors de la transcription de {image_file}: {str(e)}")


# Traiter uniquement certaines pages (ex. pages 1, 3 et 5)
process_pdfs(input_folder, output_folder, selected_pages=[2,3,4,5,6,7,8])  # Traiter toutes les pages = selected_pages=None

###################################

def list_documents(per_page=50, page=1):
    """Retrieve a paginated list of documents."""
    url = f"https://www.handwritingocr.com/api/v2/documents"
    headers = {
        "Authorization": f"Bearer {api_key_handwriting_ocr}",
        "Accept": "application/json"
    }
    params = {
        "per_page": per_page,
        "page": page
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")

documents = list_documents()
documents

###################################

def clean_file(file_path):
    """Nettoyer le contenu d'un fichier donné si son nom correspond à un motif."""
    try:
        # Vérifier si le nom correspond au motif
        file_name = os.path.basename(file_path)
        if re.match(r"page_\d+", file_name):  # Vérifier si le nom correspond au motif

            if os.path.isfile(file_path):  # Vérifier si c'est un fichier
                # Lire le contenu du fichier
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()

                # Appliquer le remplacement regex
                updated_content = re.sub(r"=== \*\*Page: 1 of 1\*\*", "", content)

                # Écrire le contenu modifié dans le fichier
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(updated_content)

                print(f"Fichier nettoyé : {file_name}")

    except Exception as e:
        print(f"Erreur lors du traitement du fichier {file_path}: {e}")

def download_document(document_id, original_file_name, output_format="txt"):
    """Download a processed document, save it with its original file name, and clean the files in the folder."""
    # URL de l'API pour télécharger les documents
    url = f"https://www.handwritingocr.com/api/v2/documents/{document_id}.{output_format}"
    headers = {
        "Authorization": f"Bearer {api_key_handwriting_ocr}",
        "Accept": "application/json"
    }

    # Nettoyer le nom du fichier original pour extraire la base et le suffixe
    base_name = re.sub(r"__page_\d+", "", original_file_name)  # Supprimer la partie `__page_x`
    base_name = re.sub(r"\.pdf$", "", base_name)  # Supprimer `_pdf` s'il existe dans le nom du dossier
    suffix = re.search(r"page_\d+", original_file_name)  # Extraire le suffixe comme `page_5`
    suffix = suffix.group() if suffix else base_name  # "document"

    # Créer un sous-dossier basé sur le nom de base
    folder_path = os.path.join(output_folder, base_name)
    os.makedirs(folder_path, exist_ok=True)

    # Chemin complet pour enregistrer le fichier avec le suffixe comme nom
    file_path = os.path.join(folder_path, f"{suffix}.{output_format}")

    # Télécharger et sauvegarder le fichier
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        with open(file_path, "wb") as file:
            file.write(response.content)
        print(f"Document {suffix} téléchargé avec succès dans '{folder_path}'!")

        # Nettoyer le fichier téléchargé
        clean_file(file_path)

    else:
        print(f"Échec du téléchargement du document {document_id}: {response.status_code}, {response.text}")

def download_all_documents(documents):
    """Télécharger tous les documents en boucle."""

    os.makedirs(output_folder, exist_ok=True)  # Créer le dossier pour tous les téléchargements
    for document in documents:
        document_id = document.get('document_id')  # Obtenir l'ID du document
        original_file_name = document.get('original_file_name', f"document_{document_id}")  # Nom par défaut si absent
        if document_id:  # Vérifier que l'ID existe
            try:
                # Retirer les extensions si nécessaire
                original_file_name = original_file_name.rsplit('.', 1)[0]  
                download_document(document_id, original_file_name, output_format="txt")  # Format ajustable
            except Exception as e:
                print(f"Erreur lors du téléchargement du document {document_id}: {e}")

# Exemple d'utilisation
documents = list_documents()  # Supposons que cette fonction retourne une liste de dictionnaires
download_all_documents(documents)

###################################

# Parcourir les sous-dossiers
for folder_name in os.listdir(output_folder):
    folder_path = os.path.join(output_folder, folder_name)
    if os.path.isdir(folder_path):
        # Définir le chemin du fichier de sortie avec "_Combine"
        output_file_path = os.path.join(folder_path, f"{folder_name}_Combine.txt")
        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            # Parcourir tous les fichiers page_*.txt dans le sous-dossier
            for file_name in sorted(os.listdir(folder_path)):
                if file_name.startswith("page_") and file_name.endswith(".txt"):
                    file_path = os.path.join(folder_path, file_name)
                    with open(file_path, 'r', encoding='utf-8') as input_file:
                        # Écrire le contenu dans le fichier de sortie
                        output_file.write(input_file.read())
                        output_file.write("\n")  # Ajouter une ligne vide entre les pages

print("Tous les fichiers like 'page_' ont été combinés et nommés avec le suffixe '_Combine'.")

###################################

# Parcours de tous les sous-dossiers et fichiers
for root, dirs, files in os.walk(output_folder):
    for file in files:
        # Vérifie si le nom du fichier correspond au motif
        new_name = re.sub(r".+__", "", file)
        if new_name != file:  # Si un remplacement a été effectué
            old_path = os.path.join(root, file)
            new_path = os.path.join(root, new_name)

            # Supprime le fichier existant avant de renommer
            if os.path.exists(new_path):
                os.remove(new_path)  # Écrase en supprimant le fichier existant

            # Renomme le fichier
            os.rename(old_path, new_path)
            print(f"Renommé : {old_path} -> {new_path}")

###################################

# One prompt_for_each_page per run
def txt_file_to_gpt(txt_file_path, sys_prompt, user_prompt):
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

###################################

txt_file = "C:/Users/Guillaume.Cote/Documents/GitHub_Arpenteur/Document du Registre Foncier PNG_/AL_37_20_158_RB_pdf/AL_37_20_158_RB_pdf_Combine.txt"
sys_prompt = "Tu es un notaire/arpenteur et je suis un client."
user_prompt = "Parlez-moi de ce document, s'il vous plaît. Soyez précis."

completions_data = txt_file_to_gpt(txt_file, sys_prompt, user_prompt)
completions_data

###################################