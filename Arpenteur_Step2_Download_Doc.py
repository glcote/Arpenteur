import logging
from Utils import output_folder, list_documents, download_document, combine_page_files


###################################
# Main Execution

if __name__ == "__main__":
    logging.info("Starting PDF to image conversion and processing.")
    documents = list_documents()
    for document in documents:
        document_id = document.get("document_id")
        original_file_name = document.get("original_file_name", "document")
        if document_id:
            download_document(document_id, original_file_name)
    combine_page_files(output_folder)
    logging.info("All page files have been combined and saved.")
