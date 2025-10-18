from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251018_0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint("price >= 0", name="items_price_non_negative"),
    )
    op.create_index("ix_items_deleted", "items", ["deleted"])
    op.create_index("ix_items_price", "items", ["price"])

    op.create_table(
        "carts",
        sa.Column("id", sa.Integer(), primary_key=True),
    )

    op.create_table(
        "cart_items",
        sa.Column("cart_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["cart_id"], ["carts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.PrimaryKeyConstraint("cart_id", "item_id", name="pk_cart_items"),
        sa.UniqueConstraint("cart_id", "item_id", name="uq_cart_item"),
        sa.CheckConstraint("quantity > 0", name="cart_items_quantity_positive"),
    )

def downgrade() -> None:
    op.drop_table("cart_items")
    op.drop_table("carts")
    op.drop_index("ix_items_price", table_name="items")
    op.drop_index("ix_items_deleted", table_name="items")
    op.drop_table("items")
