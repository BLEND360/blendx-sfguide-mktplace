"""
Chat message models for BlendX Core.

Defines SQLAlchemy model for storing conversation context in the chat interface.
"""

import uuid

from sqlalchemy import Column, DateTime, String, Text, func

from app.database.models import Base


class ChatMessage(Base):
    """
    SQLAlchemy model for the chat_messages table.

    Stores conversation messages from the natural language generator chat interface,
    including user messages, assistant responses, and system messages.
    """

    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=True)
    content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    user_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    def __repr__(self):
        return f"<ChatMessage(id='{self.id}', chat_id='{self.chat_id}', role='{self.role}')>"
