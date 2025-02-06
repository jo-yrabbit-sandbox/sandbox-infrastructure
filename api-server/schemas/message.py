from typing import TypedDict, List, Optional, Union
from datetime import datetime
from enum import Enum

class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    STICKER = "sticker"
    AUDIO = "audio"
    COMMAND = "cmd"

class MessageMetadata(TypedDict):
    created_at: str
    source_id: str           # Who sent it (bot/client id)
    msg_type: MessageType    # Type of content
    thread_id: Optional[str] # For message threading
    tags: List[str]          # For categorization/searching
    size_bytes: int          # Content size tracking
    content_hash: str        # For deduplication/integrity

# Different content type structures
class TextContent(TypedDict):
    text: str
    language: Optional[str]

class ImageContent(TypedDict):
    url: str
    width: int
    height: int
    format: str
    thumbnail_url: Optional[str]

class Message(TypedDict):
    id: str
    content: Union[TextContent, ImageContent]  # Varies by message type
    metadata: MessageMetadata