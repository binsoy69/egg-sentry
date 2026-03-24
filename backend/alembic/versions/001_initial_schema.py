"""Initial EggSentry schema."""

from alembic import op
import sqlalchemy as sa


revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.String(length=50), nullable=False),
        sa.Column("api_key", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("num_cages", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("num_chickens", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("min_size_threshold", sa.Float(), nullable=False, server_default="40"),
        sa.Column("max_size_threshold", sa.Float(), nullable=False, server_default="80"),
        sa.Column("confidence_threshold", sa.Float(), nullable=False, server_default="0.85"),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_devices_id"), "devices", ["id"], unique=False)
    op.create_index(op.f("ix_devices_device_id"), "devices", ["device_id"], unique=True)
    op.create_index(op.f("ix_devices_api_key"), "devices", ["api_key"], unique=True)

    op.create_table(
        "egg_detections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("size", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("bbox_area_normalized", sa.Float(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_egg_detections_id"), "egg_detections", ["id"], unique=False)
    op.create_index(op.f("ix_egg_detections_device_id"), "egg_detections", ["device_id"], unique=False)
    op.create_index(op.f("ix_egg_detections_size"), "egg_detections", ["size"], unique=False)
    op.create_index(op.f("ix_egg_detections_detected_at"), "egg_detections", ["detected_at"], unique=False)

    op.create_table(
        "count_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("size_breakdown", sa.JSON(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_count_snapshots_id"), "count_snapshots", ["id"], unique=False)
    op.create_index(op.f("ix_count_snapshots_device_id"), "count_snapshots", ["device_id"], unique=False)
    op.create_index(op.f("ix_count_snapshots_captured_at"), "count_snapshots", ["captured_at"], unique=False)

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_dismissed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_alerts_id"), "alerts", ["id"], unique=False)
    op.create_index(op.f("ix_alerts_device_id"), "alerts", ["device_id"], unique=False)
    op.create_index(op.f("ix_alerts_type"), "alerts", ["type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_alerts_type"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_device_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_id"), table_name="alerts")
    op.drop_table("alerts")

    op.drop_index(op.f("ix_count_snapshots_captured_at"), table_name="count_snapshots")
    op.drop_index(op.f("ix_count_snapshots_device_id"), table_name="count_snapshots")
    op.drop_index(op.f("ix_count_snapshots_id"), table_name="count_snapshots")
    op.drop_table("count_snapshots")

    op.drop_index(op.f("ix_egg_detections_detected_at"), table_name="egg_detections")
    op.drop_index(op.f("ix_egg_detections_size"), table_name="egg_detections")
    op.drop_index(op.f("ix_egg_detections_device_id"), table_name="egg_detections")
    op.drop_index(op.f("ix_egg_detections_id"), table_name="egg_detections")
    op.drop_table("egg_detections")

    op.drop_index(op.f("ix_devices_api_key"), table_name="devices")
    op.drop_index(op.f("ix_devices_device_id"), table_name="devices")
    op.drop_index(op.f("ix_devices_id"), table_name="devices")
    op.drop_table("devices")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
