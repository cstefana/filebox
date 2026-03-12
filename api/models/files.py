from datetime import datetime
from pydantic import BaseModel


class FileResponse(BaseModel):
    id: int
    user_id: int
    original_filename: str
    stored_filename: str
    content_type: str
    size: int
    path: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FileListResponse(BaseModel):
    files: list[FileResponse]
