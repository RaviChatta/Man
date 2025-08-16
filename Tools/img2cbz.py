import os
import zipfile
from loguru import logger

def images_to_cbz(image_files, cbz_output_path):
    """
    Convert a list of image files into a CBZ archive.

    Args:
        image_files (list): List of image file paths to include.
        cbz_output_path (str): Path to the output CBZ file.
    """
    try:
        if not image_files:
            logger.warning("No images provided for CBZ creation.")
            return

        os.makedirs(os.path.dirname(cbz_output_path), exist_ok=True)

        with zipfile.ZipFile(cbz_output_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for image_file_path in image_files:
                if os.path.exists(image_file_path):
                    file_name = os.path.basename(image_file_path)
                    zip_file.write(image_file_path, arcname=file_name)
                else:
                    logger.warning(f"Skipped missing image: {image_file_path}")

        logger.info(f"CBZ created successfully at {cbz_output_path}")

    except Exception as e:
        logger.exception(f"Error creating CBZ: {e}")
        return e
