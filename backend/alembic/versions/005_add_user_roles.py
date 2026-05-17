"""Add role support to users."""

from alembic import op
import sqlalchemy as sa


revision = "005_add_user_roles"
down_revision = "004_collection_sizes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=30), nullable=False, server_default="viewer"),
    )
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
    op.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")
    op.execute("UPDATE users SET role = 'viewer' WHERE username = 'viewer'")
    op.execute("UPDATE users SET role = 'history_editor' WHERE username = 'editor'")


def downgrade() -> None:
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_column("users", "role")
