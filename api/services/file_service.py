from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db.models import FileRecord


class FileService:
    """Service layer for file database operations."""

    @staticmethod
    def create_file_record(
        db: Session,
        user_id: int,
        original_filename: str,
        stored_filename: str,
        content_type: str,
        size: int,
        path: str,
    ) -> FileRecord:
        """Create a new file record in the database."""
        file_record = FileRecord(
            user_id=user_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=content_type,
            size=size,
            path=path,
        )
        db.add(file_record)
        db.commit()
        db.refresh(file_record)
        return file_record

    @staticmethod
    def get_user_files(db: Session, user_id: int) -> list[FileRecord]:
        """Get all files belonging to a user."""
        return db.query(FileRecord).filter(FileRecord.user_id == user_id).all()

    @staticmethod
    def get_file_by_id(db: Session, file_id: int) -> FileRecord:
        """Get a file by ID. Raises 404 if not found."""
        file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )
        return file_record

    @staticmethod
    def verify_file_ownership(file_record: FileRecord, user_id: int) -> None:
        """Verify that a file belongs to a user. Raises 403 if not."""
        if file_record.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this file",
            )
