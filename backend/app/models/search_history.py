"""Search history model."""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class SearchHistory(Base, TimestampMixin):
    """Search history model for tracking user searches."""
    
    __tablename__ = "search_history"
    
    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(1000), nullable=False, index=True)
    search_type = Column(String(50), nullable=False, default="general")  # general, semantic, full_text
    filters = Column(JSON, default=dict, nullable=False)
    results_count = Column(Integer, default=0, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="search_history")
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<SearchHistory(id={self.id}, query='{self.query}', user_id={self.user_id})>"