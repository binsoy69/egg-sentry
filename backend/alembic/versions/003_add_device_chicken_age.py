"""Add shared chicken age fields to devices."""

from alembic import op
import sqlalchemy as sa


revision = "003_add_device_chicken_age"
down_revision = "002_add_egg_collections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("age_of_chicken_total_days", sa.Integer(), nullable=True))
    op.add_column("devices", sa.Column("age_of_chicken_set_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("devices", "age_of_chicken_set_at")
    op.drop_column("devices", "age_of_chicken_total_days")
