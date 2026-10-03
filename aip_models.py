# AIP协议核心数据模型
# 简化版，基于ACPs SDK的核心概念

from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Any, Dict
from datetime import datetime
from enum import Enum


class SenderRole(str, Enum):
    """发送者角色"""
    LEADER = "leader"
    PARTNER = "partner"
    USER = "user"


class CommandType(str, Enum):
    """任务命令类型"""
    START = "start"
    GET = "get"
    CONTINUE = "continue"
    COMPLETE = "complete"
    CANCEL = "cancel"


class TaskStatusType(str, Enum):
    """任务状态"""
    ACCEPTED = "accepted"
    WORKING = "working"
    AWAITING_INPUT = "awaiting-input"
    AWAITING_COMPLETION = "awaiting-completion"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELED = "canceled"


class DataItem(BaseModel):
    """数据项（兼容ACPs格式）"""
    type: str
    text: Optional[str] = None
    data: Optional[Dict] = None
    name: Optional[str] = None
    mimeType: Optional[str] = None
    bytes: Optional[str] = None


class TextDataItem(BaseModel):
    """文本数据项"""
    type: Literal["text"] = "text"
    text: str


class Message(BaseModel):
    """AIP消息基类"""
    id: str = Field(default_factory=lambda: f"msg_{datetime.now().timestamp()}")
    sentAt: str = Field(default_factory=lambda: datetime.now().isoformat())
    senderRole: SenderRole
    senderId: str
    sessionId: Optional[str] = None
    dataItems: Optional[List[DataItem]] = None


class TaskCommand(Message):
    """任务命令（ACPs标准格式）"""
    command: CommandType
    taskId: str
    mentions: Optional[List[str]] = None


class TaskStatus(BaseModel):
    """任务状态"""
    state: str
    stateChangedAt: str = Field(default_factory=lambda: datetime.now().isoformat())
    message: Optional[str] = None


class Product(BaseModel):
    """智能体产出物（ACPs标准格式）"""
    id: str
    name: str
    dataItems: List[Dict]


class TaskResult(Message):
    """任务结果（ACPs标准格式）"""
    taskId: str
    status: Dict  # TaskStatus的字典表示
    products: List[Dict] = []  # Product的字典表示
