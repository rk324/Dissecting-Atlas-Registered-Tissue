import os
import sys
from pathlib import Path
from zipfile import ZipFile
import requests


RECORD_ID = 17849564  # Zenodo record id containing the atlases archive
BACKUP_DOWNLOAD_URL = f"https://zenodo.org/record/{RECORD_ID}/files/atlases.zip"
LAST_KNOWN_SIZE = 2851427875  # last known size in bytes of atlas.zip

# Default destination: package-local `atlases` directory next to this module
DEST_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "atlases"
)


def download_atlases():
    """
    Download atlas archive from Zenodo (RECORD_ID) and extract into
    the package-local `atlases` directory (DEFAULT_DEST_DIR).

    Returns
    -------
    dest_dir : str
        Returns the destination directory (str).
    """
    # Check if atlases already exist
    if os.path.exists(DEST_DIR) and len(os.listdir(DEST_DIR)) > 0:
        # Atlases may already exist, ask user to confirm download
        print(f"Atlases directory '{DEST_DIR}' already exists and is not empty. Proceeding may overwrite existing files.")
        response = input("Proceed (y/n)? ")
        
        # Repeat until valid response
        while response.lower() not in ['y', 'n']:
            print(f"Your response ('{response}') was not one of 'y' or 'n'.")
            response = input("Proceed (y/n)? ")
        
        # Cancel download if user responds 'n'
        if response.lower() == 'n':
            print("Download cancelled.")
            return

    # Create destination directory if it doesn't exist
    dest_dir = Path(DEST_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Get record
    print("Fetching atlas metadata from Zenodo...",end="")
    try:
        record = requests.get(f"https://zenodo.org/api/records/{RECORD_ID}")
        record.raise_for_status()
        record = record.json()
        download_url = record['files'][0]['links']['self']
        size = record['files'][0]['size']
        print("DONE")
    except:
        print("FAILED")
        print("Failed to fetch metadata from Zenodo. Using backup download URL.")
        download_url = BACKUP_DOWNLOAD_URL
        size = LAST_KNOWN_SIZE

    # Download .zip file from zenodo
    dest_file = os.path.join(dest_dir, "atlases.zip")
    with requests.get(download_url, stream=True) as r:
        r.raise_for_status()
        with open(dest_file, 'wb') as f:
            print(f"Downloading atlases.zip...(0/{size})",end='\r')
            downloaded = 0
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    print(f"Downloading atlases.zip...({downloaded}/{size})", end='\r')
            print("Downloading atlases.zip.......................................DONE")
        
    # Extract .zip file
    print("Extracting atlases.zip", end='...')
    with ZipFile(dest_file, 'r') as zip_ref:
        zip_ref.extractall(dest_dir)
        print("DONE")

    # Remove .zip file
    print("Removing atlases.zip", end='...')
    os.remove(dest_file)
    print("DONE")

    print(f"Atlases available at: {DEST_DIR}")

def main():
    download_atlases()
    return 0


if __name__ == '__main__':
    sys.exit(main())
