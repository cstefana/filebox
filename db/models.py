from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import TSVECTOR

from db.database import Base

class UserRecord(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    password_hash = Column(String, nullable=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to files
    files = relationship("FileRecord", back_populates="user")


class FileRecord(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to user
    user = relationship("UserRecord", back_populates="files")
    content = relationship("FileContentRecord", back_populates="file", uselist=False, cascade="all, delete-orphan")


class FileContentRecord(Base):
    __tablename__ = "file_content"

    file_id = Column(Integer, ForeignKey("files.id"), primary_key=True)
    # Use a GIN index in Postgres for efficient full-text search.
    # We declare the index explicitly instead of using index=True to avoid a default btree index,
    # which can hit Postgres row-size limits for large tsvectors.
    content_tsv = Column(TSVECTOR, nullable=False)

    __table_args__ = (
        Index(
            "ix_file_content_content_tsv",
            "content_tsv",
            postgresql_using="gin",
        ),
    )

    file = relationship("FileRecord", back_populates="content")