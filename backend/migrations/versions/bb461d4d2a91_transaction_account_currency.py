"""Preserve the bank-reported transaction amount in the account currency."""

import sqlalchemy as sa
from alembic import op

revision = "bb461d4d2a91"
down_revision = "5e24857799e6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("transactions", sa.Column("amount_in_account_currency", sa.Numeric(), nullable=True))


def downgrade():
    op.drop_column("transactions", "amount_in_account_currency")
