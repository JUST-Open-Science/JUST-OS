from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import json

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive"]


def authenticate(credentials_path):
    """Authenticate with Google Drive API."""
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_info(
            json.loads(open("token.json").read()), SCOPES
        )

    # If credentials don't exist or are invalid, run the OAuth flow
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def upload_file(file_path, folder_id, creds, exists_ok=False, remote_filename=None):
    """
    Upload a file to the specified folder in Google Drive.

    Args:
        file_path: Path to the file to upload
        folder_id: ID of the folder to upload to
        creds: Google Drive API credentials
        exists_ok: If True, replace existing file with same name
                  If False, skip upload if file with same name exists
        remote_filename: Custom filename to use in Google Drive (default: original filename)

    Returns:
        File ID if uploaded/updated, None if skipped due to exists_ok=False
    """
    # Build the Drive API client
    service = build("drive", "v3", credentials=creds)

    # Get the file name from the path or use the provided remote_filename
    file_name = remote_filename if remote_filename else os.path.basename(file_path)

    # Check if file already exists in the folder
    query = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
    results = (
        service.files()
        .list(q=query, spaces="drive", fields="files(id, name)")
        .execute()
    )
    existing_files = results.get("files", [])

    # Prepare the media upload
    media = MediaFileUpload(file_path, resumable=True)

    if existing_files:
        # File already exists
        file_id = existing_files[0]["id"]

        if exists_ok:
            # Update the existing file
            service.files().update(fileId=file_id, media_body=media).execute()
            print(f"Updated existing file - File ID: {file_id}")
            return file_id
        else:
            # Skip the upload
            print(
                f'File "{file_name}" already exists (ID: {file_id}). Skipping upload.'
            )
            return None
    else:
        # No existing file with this name, create a new one
        file_metadata = {"name": file_name, "parents": [folder_id]}

        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )

        print(f"Created new file - File ID: {file.get('id')}")
        return file.get("id")


def upload_folder(
    local_folder_path, parent_folder_id, creds, exists_ok=False, remote_foldername=None
):
    """
    Upload a local folder and its contents to Google Drive.

    Args:
        local_folder_path: Path to the local folder to upload
        parent_folder_id: ID of the parent folder in Google Drive
        creds: Google Drive API credentials
        exists_ok: If True, replace existing files with same name
                  If False, skip upload if file with same name exists
        remote_foldername: Custom folder name to use in Google Drive (default: original folder name)

    Returns:
        Folder ID of the created/existing folder in Google Drive
    """
    # Build the Drive API client
    service = build("drive", "v3", credentials=creds)

    # Get the folder name from the path or use the provided remote_foldername
    folder_name = (
        remote_foldername if remote_foldername else os.path.basename(local_folder_path)
    )

    # Check if folder already exists in the parent folder
    query = f"name = '{folder_name}' and '{parent_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = (
        service.files()
        .list(q=query, spaces="drive", fields="files(id, name)")
        .execute()
    )
    existing_folders = results.get("files", [])

    if existing_folders:
        # Folder already exists
        folder_id = existing_folders[0]["id"]
        print(
            f'Folder "{folder_name}" already exists (ID: {folder_id}). Using existing folder.'
        )
    else:
        # Create a new folder
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_folder_id],
        }
        folder = service.files().create(body=folder_metadata, fields="id").execute()
        folder_id = folder.get("id")
        print(f'Created new folder "{folder_name}" (ID: {folder_id}).')

    # Upload all files and subfolders in the local folder
    for item in os.listdir(local_folder_path):
        item_path = os.path.join(local_folder_path, item)

        if os.path.isfile(item_path):
            # Upload file
            upload_file(item_path, folder_id, creds, exists_ok=exists_ok)
        elif os.path.isdir(item_path):
            # Recursively upload subfolder
            upload_folder(item_path, folder_id, creds, exists_ok=exists_ok)

    return folder_id
