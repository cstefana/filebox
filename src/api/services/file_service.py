from fastapi import HTTPException, status
from fastapi import UploadFile
from pathlib import Path
import os
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.services.embedding_service import embed_text, embed_texts
from api.services.groq_service import query_files
from db.models import FileChunkRecord, FileRecord
from utils.files import save_uploaded_file

# Get the project root (two levels up from this file: src/api/services -> project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

_CHUNK_SIZE = 1000  # characters per chunk
_CHUNK_OVERLAP = 200  # overlap between consecutive chunks


def _chunk_text(text: str) -> list[str]:
    """Split *text* into overlapping fixed-size chunks."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + _CHUNK_SIZE])
        start += _CHUNK_SIZE - _CHUNK_OVERLAP
    return chunks


class FileService:
    """Service layer for file database operations."""

    @staticmethod
    def resolve_file_path(relative_or_absolute_path: str) -> Path:
        """Resolve a file path that may be relative or absolute.
        
        Relative paths are resolved from the project root.
        Absolute paths are used as-is.
        """
        if relative_or_absolute_path.startswith("/"):
            return Path(relative_or_absolute_path)
        else:
            return PROJECT_ROOT / relative_or_absolute_path

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
            chunks = _chunk_text(text_content)

            # Batch-embed all chunks in a single API call.
            try:
                embeddings = embed_texts(chunks)
            except Exception:
                embeddings = [None] * len(chunks)

            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_record = FileChunkRecord(
                    file_id=record.id,
                    chunk_index=idx,
                    content=chunk,
                    content_tsv=func.to_tsvector("english", chunk),
                    embedding=embedding,
                )
                db.add(chunk_record)

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
        """Search file content by text and rank results by semantic relevance using embeddings.
        
        Uses pgvector cosine distance to rank files by semantic relevance of their chunks.
        Falls back to PostgreSQL full-text search score if embeddings are unavailable.
        """
        # Embed the query to compare against chunk embeddings
        try:
            query_embedding = embed_text(query_text)
            has_embedding = True
        except Exception:
            query_embedding = None
            has_embedding = False
        
        # Full-text search query
        ts_query = func.plainto_tsquery("english", query_text)
        
        if has_embedding and query_embedding:
            # Use embedding-based ranking: find the best (closest) matching chunk per file
            # Create a subquery that groups chunks by file and gets the minimum distance
            relevance_subquery = db.query(
                FileChunkRecord.file_id,
                func.min(FileChunkRecord.embedding.cosine_distance(query_embedding)).label("best_distance")
            ).join(
                FileRecord, FileChunkRecord.file_id == FileRecord.id
            ).filter(
                FileRecord.user_id == user_id,
                FileChunkRecord.content_tsv.op("@@")(ts_query),
                FileChunkRecord.embedding.isnot(None)
            ).group_by(FileChunkRecord.file_id).subquery()
            
            # Fetch files and sort by their best chunk distance (lower = more relevant)
            results = db.query(FileRecord).join(
                relevance_subquery, FileRecord.id == relevance_subquery.c.file_id
            ).order_by(relevance_subquery.c.best_distance.asc()).all()
            
            return results
        else:
            # Fallback: use full-text search with default ordering
            return (
                db.query(FileRecord)
                .join(FileChunkRecord, FileChunkRecord.file_id == FileRecord.id)
                .filter(FileRecord.user_id == user_id)
                .filter(FileChunkRecord.content_tsv.op("@@")(ts_query))
                .distinct()
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

    @staticmethod
    def query_user_files_with_ai(
        db: Session,
        user_id: int,
        user_query: str,
        file_ids: list[int] | None = None,
    ) -> tuple[str, list[int]]:
        """Query the Groq AI model about user's files.
        
        Args:
            db: Database session
            user_id: ID of the user
            user_query: Question to ask about files
            file_ids: Optional list of specific file IDs to include. 
                      If None, uses semantic search to find relevant files.
            
        Returns:
            Tuple of (response_text, list_of_file_ids_used)
            
        Raises:
            HTTPException: If no files are found or query fails
        """
        # Get files to query
        if file_ids:
            # Get specific files
            files = db.query(FileRecord).filter(
                FileRecord.id.in_(file_ids),
                FileRecord.user_id == user_id,
            ).all()
            
            if not files:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No files found with the specified IDs",
                )
            
            # Verify ownership of all requested files
            for file_record in files:
                FileService.verify_file_ownership(file_record, user_id)
        else:
            # Use semantic search to find relevant files based on the query
            files = FileService.search_user_files_by_content(db, user_id, user_query)
            
            if not files:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No relevant files found for your query",
                )
        
        # Read file contents
        file_contents = []
        valid_file_ids = []
        debug_info = []
        
        for file_record in files:
            file_path = FileService.resolve_file_path(file_record.path)
            debug_info.append(f"File {file_record.id}: {file_record.original_filename} at {file_path}")
            
            if not file_path.exists():
                debug_info.append(f"  -> Path does not exist")
                continue
            
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
                    if content:
                        # Add filename as context
                        file_contents.append(f"File: {file_record.original_filename}\n\n{content}")
                        valid_file_ids.append(file_record.id)
                        debug_info.append(f"  -> Successfully read ({len(content)} chars)")
                    else:
                        debug_info.append(f"  -> File is empty")
            except Exception as e:
                debug_info.append(f"  -> Error reading file: {str(e)}")
                continue
        
        if not file_contents:
            error_detail = "Could not read any file contents. Debug info: " + "; ".join(debug_info)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail,
            )
        
        # Query the AI model
        try:
            response = query_files(user_query, file_contents)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to query AI model: {str(e)}",
            )
        
        return response, valid_file_ids
