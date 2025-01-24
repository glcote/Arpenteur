# #############################################################
# # ------------- COUTE 1 Credit (0.08$) par PAGE ------------- #
# ##############################################################

import logging
from dotenv import load_dotenv
from Utils import input_folder, output_folder, process_pdfs

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

###################################
# Main Execution

if __name__ == "__main__":
    logging.info("Starting PDF to image conversion, transcription, and processing.")
    process_pdfs(input_folder, output_folder)
