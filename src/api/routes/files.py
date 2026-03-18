from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.models.files import FileListResponse, FileQueryRequest, FileQueryResponse, FileResponse as FileResponseModel
from api.services.file_service import FileService
from db.database import get_db
from db.models import UserRecord
from utils.jwt import get_current_user

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileResponseModel, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a file. Stored under files/{user_id}/. Returns metadata."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    service = FileService()
    file_record = await service.store_and_record(
        file=file,
        db=db,
        user_id=current_user.id,
    )

    return file_record


@router.get("/list", response_model=FileListResponse, status_code=status.HTTP_200_OK)
async def list_files(
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all files uploaded by the current user."""
    files = FileService.get_user_files(db, current_user.id)
    return {"files": files}


@router.get("/search_content", response_model=FileListResponse, status_code=status.HTTP_200_OK)
async def search_files(
    query: str = Query(..., min_length=1, description="Full-text search query"),
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search file metadata by file content for the current user."""
    files = FileService.search_user_files_by_content(db, current_user.id, query)
    return {"files": files}


@router.get("/{file_id}/info", response_model=FileResponseModel, status_code=status.HTTP_200_OK)
async def get_file_info(
    file_id: int,
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve file metadata from database by ID. Only the file owner can access it."""
    file_record = FileService.get_file_by_id(db, file_id)
    FileService.verify_file_ownership(file_record, current_user.id)
    return file_record


@router.get("/{file_id}", status_code=status.HTTP_200_OK)
async def get_file(
    file_id: int,
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download a specific file by ID. Only the file owner can access it."""
    file_record = FileService.get_file_by_id(db, file_id)
    FileService.verify_file_ownership(file_record, current_user.id)
    
    # Check if file exists on disk
    file_path = FileService.resolve_file_path(file_record.path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found on disk. Looked for: {file_path}",
        )
    
    # Return the file
    return FileResponse(
        path=file_path,
        media_type=file_record.content_type,
        filename=file_record.original_filename,
    )


@router.post("/query", response_model=FileQueryResponse, status_code=status.HTTP_200_OK)
async def query_files_with_ai(
    request: FileQueryRequest,
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Query the Groq AI model about your files using GPT-OSS-120B.
    
    Provide a question about your files and optionally specify which files to query.
    If no file IDs are provided, all your files will be used as context.
    """
    response, files_used = FileService.query_user_files_with_ai(
        db=db,
        user_id=current_user.id,
        user_query=request.query,
        file_ids=request.file_ids,
    )
    
    return FileQueryResponse(response=response, files_used=files_used)