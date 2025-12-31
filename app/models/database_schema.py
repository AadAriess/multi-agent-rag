"""
Skema database untuk Multi Agent RAG
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class Context(Base):
    __tablename__ = 'contexts'

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), nullable=False, unique=True)  # Tambahkan unique=True
    data = Column(Text, nullable=False)
    deleted_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())


class Document(Base):
    __tablename__ = 'documents'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(100), nullable=False)
    content = Column(Text)
    pages = Column(Integer)
    file_path = Column(String(255))
    content_hash = Column(String(64))  # SHA-256 hash
    last_synced = Column(DateTime)
    deleted_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())


class SearchHistory(Base):
    __tablename__ = 'search_history'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    query = Column(Text, nullable=False)
    results_summary = Column(Text)
    source_urls = Column(Text)  # JSON string
    session_id = Column(String(36))  # Tanpa foreign key constraint
    deleted_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())