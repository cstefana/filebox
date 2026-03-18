from datetime import datetime
from pydantic import BaseModel, Field


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


class FileQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Question to ask about your files")
    file_ids: list[int] | None = Field(
        None,
        description="Optional: specific file IDs to query. If not provided, all user files are used.",
    )


class FileQueryResponse(BaseModel):
    response: str = Field(..., description="The model's response to the query")
    files_used: list[int] = Field(..., description="File IDs that were used for context")
