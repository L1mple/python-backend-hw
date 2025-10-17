"""Initial migration: create items, carts and cart_items tables

Revision ID: d27f5ffd487e
Revises: 
Create Date: 2025-10-18 00:17:27.458269

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Информация о ревизии
revision: str = 'd27f5ffd487e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Обновление схемы базы данных"""
    # Создание таблицы items
    op.create_table(
        'items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id')
    )

    # Создание таблицы carts
    op.create_table(
        'carts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('price', sa.Float(), nullable=False, server_default='0.0'),
        sa.PrimaryKeyConstraint('id')
    )

    # Создание промежуточной таблицы cart_items
    op.create_table(
        'cart_items',
        sa.Column('cart_id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['cart_id'], ['carts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('cart_id', 'item_id')
    )


def downgrade() -> None:
    """Схема для отката миграции"""
    # Удаление таблицы в обратном порядке
    op.drop_table('cart_items')
    op.drop_table('carts')
    op.drop_table('items')
