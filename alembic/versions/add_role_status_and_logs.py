"""Add role, status fields and logs table

Revision ID: add_role_status_logs
Revises: 8af3eec3a7e6
Create Date: 2026-01-29 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_role_status_logs'
down_revision: Union[str, None] = '8af3eec3a7e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add role and status columns to users table
    op.add_column('users', sa.Column('role', sa.Enum('ADMIN', 'USER', 'GUEST', name='userrole'), nullable=False, server_default='USER'))
    op.add_column('users', sa.Column('status', sa.Enum('ACTIVE', 'BANNED', name='userstatus'), nullable=False, server_default='ACTIVE'))
    
    # Create logs table
    op.create_table('logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('action', sa.String(length=500), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_logs_user_id'), 'logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_logs_timestamp'), 'logs', ['timestamp'], unique=False)


def downgrade() -> None:
    # Drop logs table
    op.drop_index(op.f('ix_logs_timestamp'), table_name='logs')
    op.drop_index(op.f('ix_logs_user_id'), table_name='logs')
    op.drop_table('logs')
    
    # Drop role and status columns from users table
    op.drop_column('users', 'status')
    op.drop_column('users', 'role')
