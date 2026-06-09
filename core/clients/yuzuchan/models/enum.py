from enum import Enum


class ReviewEnum(str, Enum):
    APPROVE = "approve"
    """批准"""
    REJECT = "reject"
    """拒绝"""


class StatusEnum(str, Enum):
    """别名投票状态"""

    EXPIRED = "expired"
    """已过期"""
    CANCELED = "canceled"
    """已取消"""
    ONGOING = "ongoing"
    """进行中"""
    APPROVED = "approved"
    """已通过"""
