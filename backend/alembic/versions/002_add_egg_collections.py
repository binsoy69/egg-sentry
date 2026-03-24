"""Add egg collections support."""

from alembic import op
import sqlalchemy as sa


revision = "002_add_egg_collections"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "egg_collections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("collected_count", sa.Integer(), nullable=False),
        sa.Column("before_count", sa.Integer(), nullable=False),
        sa.Column("after_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_egg_collections_id"), "egg_collections", ["id"], unique=False)
    op.create_index(op.f("ix_egg_collections_device_id"), "egg_collections", ["device_id"], unique=False)
    op.create_index(op.f("ix_egg_collections_user_id"), "egg_collections", ["user_id"], unique=False)
    op.create_index(op.f("ix_egg_collections_source"), "egg_collections", ["source"], unique=False)
    op.create_index(op.f("ix_egg_collections_collected_at"), "egg_collections", ["collected_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_egg_collections_collected_at"), table_name="egg_collections")
    op.drop_index(op.f("ix_egg_collections_source"), table_name="egg_collections")
    op.drop_index(op.f("ix_egg_collections_user_id"), table_name="egg_collections")
    op.drop_index(op.f("ix_egg_collections_device_id"), table_name="egg_collections")
    op.drop_index(op.f("ix_egg_collections_id"), table_name="egg_collections")
    op.drop_table("egg_collections")
