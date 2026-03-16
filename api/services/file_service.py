from fastapi import HTTPException, status
from fastapi import UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import FileContentRecord, FileRecord
from utils.files import save_uploaded_file


class FileService:
    """Service layer for file database operations."""

    async def store(self, *, file: UploadFile, user_id: int) -> dict:
        """Store a file on disk and return metadata."""
        return await save_uploaded_file(file, user_id)

    async def store_and_record(
        self,
        *,
        file: UploadFile,
        user_id: int,
        db: Session,
    ) -> FileRecord:
        """Store file on disk, create file record, and persist searchable content."""
        stored = await self.store(file=file, user_id=user_id)

        record = FileRecord(
            original_filename=stored["original_filename"],
            stored_filename=stored["stored_filename"],
            content_type=stored["content_type"],
            size=stored["size"],
            path=stored["path"],
            user_id=user_id,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        raw_bytes = stored.get("raw_bytes", b"")
        try:
            text_content = raw_bytes.decode("utf-8", errors="ignore")
        except Exception:
            text_content = ""

        # Postgres text values cannot contain NUL characters.
        # Binary uploads may decode to strings that still include "\x00".
        text_content = text_content.replace("\x00", "").strip()

        if text_content:
            content_record = FileContentRecord(
                file_id=record.id,
                content_tsv=func.to_tsvector("english", text_content),
            )
            db.add(content_record)
            db.commit()

        db.refresh(record)
        return record

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
    def search_user_files_by_content(db: Session, user_id: int, query_text: str) -> list[FileRecord]:
        """Search file metadata by indexed file content for a user."""
        ts_query = func.plainto_tsquery("english", query_text)
        return (
            db.query(FileRecord)
            .join(FileContentRecord, FileContentRecord.file_id == FileRecord.id)
            .filter(FileRecord.user_id == user_id)
            .filter(FileContentRecord.content_tsv.op("@@")(ts_query))
            .order_by(FileRecord.created_at.desc())
            .all()
        )

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
