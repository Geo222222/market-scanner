"""Realtime scalper console tables"""

from alembic import op
import sqlalchemy as sa

revision = "20241004_scalper_console"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("name", sa.String(64), primary_key=True),
        sa.Column("weights", sa.JSON(), nullable=True),
        sa.Column("manipulation_threshold", sa.Float(), nullable=True),
        sa.Column("notional", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "watchlists",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "watchlist_symbols",
        sa.Column("watchlist_id", sa.Integer(), sa.ForeignKey("watchlists.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("symbol", sa.String(80), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.create_table(
        "profile_presets",
        sa.Column("name", sa.String(64), primary_key=True),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("profile_presets")
    op.drop_table("watchlist_symbols")
    op.drop_table("watchlists")
    op.drop_table("user_profiles")
