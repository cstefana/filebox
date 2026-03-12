from pathlib import Path
import uuid
from datetime import datetime

from fastapi import UploadFile


UPLOAD_DIR = Path("files")


async def save_uploaded_file(file: UploadFile, user_id: int) -> dict:
    """
    Save an uploaded file to disk under files/{user_id}/.
    Generates a unique filename using timestamp + random UUID.
    
    Args:
        file: The UploadFile object
        user_id: The ID of the user uploading the file
        
    Returns:
        Dictionary with file metadata (original_filename, stored_filename, content_type, size, path)
    """
    # Extract original filename and extension
    original_name = Path(file.filename).name
    file_ext = Path(file.filename).suffix
    
    # Generate unique filename: timestamp_uuid.ext
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    stored_filename = f"{timestamp}_{unique_id}{file_ext}"
    
    # Create user directory
    user_dir = UPLOAD_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = user_dir / stored_filename

    # Read and write file content
    content = await file.read()
    dest.write_bytes(content)

    return {
        "original_filename": original_name,
        "stored_filename": stored_filename,
        "content_type": file.content_type or "application/octet-stream",
        "size": len(content),
        "path": str(dest),
    }
