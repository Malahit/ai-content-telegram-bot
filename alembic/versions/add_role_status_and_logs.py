"""Add role, status fields and logs table

Revision ID: add_role_status_logs
Revises: 8af3eec3a7e6
Create Date: 2026-01-29 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'add_role_status_logs'
down_revision: Union[str, None] = '8af3eec3a7e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table, column):
    insp = inspect(conn)
    return column in [c['name'] for c in insp.get_columns(table)]


def _table_exists(conn, table):
    insp = inspect(conn)
    return table in insp.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()

    userrole = sa.Enum('ADMIN', 'USER', 'GUEST', name='userrole')
    userrole.create(bind, checkfirst=True)

    userstatus = sa.Enum('ACTIVE', 'BANNED', name='userstatus')
    userstatus.create(bind, checkfirst=True)

    if not _column_exists(bind, 'users', 'role'):
        op.add_column('users', sa.Column('role', sa.Enum('ADMIN', 'USER', 'GUEST', name='userrole'), nullable=False, server_default='USER'))

    if not _column_exists(bind, 'users', 'status'):
        op.add_column('users', sa.Column('status', sa.Enum('ACTIVE', 'BANNED', name='userstatus'), nullable=False, server_default='ACTIVE'))

    if not _table_exists(bind, 'logs'):
        op.create_table('logs',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('action', sa.String(length=500), nullable=False),
            sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_logs_user_id'), 'logs', ['user_id'], unique=False)
        op.create_index(op.f('ix_logs_timestamp'), 'logs', ['timestamp'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(op.f('ix_logs_timestamp'), table_name='logs')
    op.drop_index(op.f('ix_logs_user_id'), table_name='logs')
    op.drop_table('logs')

    op.drop_column('users', 'status')
    op.drop_column('users', 'role')

    userstatus = sa.Enum('ACTIVE', 'BANNED', name='userstatus')
    userstatus.drop(bind, checkfirst=True)

    userrole = sa.Enum('ADMIN', 'USER', 'GUEST', name='userrole')
    userrole.drop(bind, checkfirst=True)
