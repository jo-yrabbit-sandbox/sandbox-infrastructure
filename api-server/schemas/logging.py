from typing import TypedDict, Optional, Any, List
from enum import Enum

class RedisOperation(Enum):
    GET = "get"
    SET = "set"
    DELETE = "delete"
    INDEX = "index"
    SEARCH = "search"

# class OperationLog(TypedDict):
#     timestamp: str
#     operation: RedisOperation
#     duration_ms: float
#     success: bool
#     message_id: Optional[str]
#     indexes_affected: List[str]
#     error: Optional[str]

# class SystemMetrics(TypedDict):
#     redis_memory_used: int
#     total_messages: int
#     total_indexes: int
#     operation_count: int