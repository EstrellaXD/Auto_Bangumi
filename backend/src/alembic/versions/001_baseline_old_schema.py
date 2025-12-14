"""baseline old schema

Revision ID: 001
Revises:
Create Date: 2024-12-13

这是旧数据库结构的基线版本，不执行任何操作。
用于标记现有旧数据库的起点。
"""

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """旧结构基线，不执行任何操作"""
    pass


def downgrade() -> None:
    pass
