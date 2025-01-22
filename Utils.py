import os
import re

# Fonction pour récupérer les fichiers .txt contenant "_Combine" dans leur nom
def get_combine_txt_files_in_subfolders(folder):
    txt_files = []
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith('.txt') and '_Combine' in file:
                full_path = os.path.join(root, file)
                txt_files.append(full_path)
    return txt_files

# Fonction pour récupérer tous les fichiers PNG dans le dossier du fichier sélectionné
def get_png_files_in_same_folder(txt_file):
    folder = os.path.dirname(txt_file)
    # Récupérer tous les fichiers PNG
    png_files = [os.path.join(folder, file) for file in os.listdir(folder) if file.endswith('.png')]
    
    # Trier les fichiers PNG par numéro extrait du nom (e.g., "page_{number}.png")
    def extract_page_number(filename):
        match = re.search(r'page_(\d+)\.png', filename)
        return int(match.group(1)) if match else float('inf')  # Assurer une valeur élevée si le numéro est manquant

    png_files.sort(key=lambda x: extract_page_number(os.path.basename(x)))
    return png_files
