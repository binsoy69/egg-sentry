"""Add size breakdown storage to egg collections."""

from alembic import op
import sqlalchemy as sa


revision = "004_add_collection_size_breakdown"
down_revision = "003_add_device_chicken_age"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("egg_collections", sa.Column("size_breakdown", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("egg_collections", "size_breakdown")
