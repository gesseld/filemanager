"""Document model."""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class Document(Base, TimestampMixin):
    """Document model for file management."""
    
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    checksum = Column(String(64), nullable=False, unique=True, index=True)
    status = Column(String(20), default="pending", nullable=False)
    is_processed = Column(Boolean, default=False, nullable=False)
    is_indexed = Column(Boolean, default=False, nullable=False)
    content_preview = Column(Text, nullable=True)
    extracted_text = Column(Text, nullable=True)
    extracted_text_path = Column(String(1000), nullable=True)
    ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(JSON, nullable=True)
    document_metadata = Column(JSON, default=dict, nullable=False)
    extracted_metadata = Column(JSON, default=dict, nullable=False)
    tags = Column(JSON, default=list, nullable=False)
    
    # Text extraction status
    text_extraction_status = Column(String(20), default="pending", nullable=False)
    ocr_status = Column(String(20), default="pending", nullable=False)
    
    # Foreign keys
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="documents")
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<Document(id={self.id}, title='{self.title}', owner_id={self.owner_id})>"