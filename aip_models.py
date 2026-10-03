"""
AIP协议核心数据模型
完全对齐ACPs官方SDK: acps-sdk/acps_sdk/aip/aip_base_model.py
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Any, Dict, Union
from datetime import datetime
from enum import Enum


class SenderRole(str, Enum):
    """发送者角色"""
    LEADER = "leader"
    PARTNER = "partner"


class TaskState(str, Enum):
    """任务状态枚举（对齐官方SDK）"""
    ACCEPTED = "accepted"
    WORKING = "working"
    AWAITING_INPUT = "awaiting-input"
    AWAITING_COMPLETION = "awaiting-completion"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELED = "canceled"


class TaskCommandType(str, Enum):
    """任务命令类型（对齐官方SDK）"""
    GET = "get"
    START = "start"
    CONTINUE = "continue"
    CANCEL = "cancel"
    COMPLETE = "complete"
    RE_STREAM = "re-stream"


# =============================================================================
# 数据项类型（对齐官方SDK）
# =============================================================================

class DataItemBase(BaseModel):
    """数据项基类"""
    metadata: Optional[Dict[str, Any]] = None


class TextDataItem(DataItemBase):
    """文本数据项"""
    type: Literal["text"] = "text"
    text: str


class FileDataItem(DataItemBase):
    """文件数据项"""
    type: Literal["file"] = "file"
    name: Optional[str] = None
    mimeType: Optional[str] = None
    uri: Optional[str] = None
    bytes: Optional[str] = None


class StructuredDataItem(DataItemBase):
    """结构化数据项"""
    type: Literal["data"] = "data"
    data: Dict[str, Any]


DataItem = Union[TextDataItem, FileDataItem, StructuredDataItem]


# =============================================================================
# 任务状态和产出物（对齐官方SDK）
# =============================================================================

class TaskStatus(BaseModel):
    """任务状态"""
    state: TaskState
    stateChangedAt: str = Field(default_factory=lambda: datetime.now().isoformat())
    dataItems: Optional[List[DataItem]] = None


class Product(BaseModel):
    """产出物（对齐官方SDK）"""
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    dataItems: List[DataItem]


# =============================================================================
# AIP消息类型（对齐官方SDK）
# =============================================================================

class Message(BaseModel):
    """AIP消息基类"""
    type: str = "message"
    id: str = Field(default_factory=lambda: f"msg_{int(datetime.now().timestamp() * 1000)}")
    sentAt: str = Field(default_factory=lambda: datetime.now().isoformat())
    senderRole: SenderRole
    senderId: str
    mentions: Optional[Union[Literal["all"], List[str]]] = None
    dataItems: Optional[List[DataItem]] = None
    groupId: Optional[str] = None
    sessionId: Optional[str] = None


class TaskCommand(Message):
    """任务命令（对齐官方SDK）"""
    type: Literal["task-command"] = "task-command"
    command: TaskCommandType
    commandParams: Optional[Dict[str, Any]] = None
    taskId: Optional[str] = None


class TaskResult(Message):
    """任务结果（对齐官方SDK）"""
    type: Literal["task-result"] = "task-result"
    taskId: str
    status: TaskStatus  # 注意：这是对象，不是Dict！
    products: Optional[List[Product]] = None
    commandHistory: Optional[List[TaskCommand]] = None
    statusHistory: Optional[List[TaskStatus]] = None
