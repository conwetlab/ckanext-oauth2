"""Create user_token table.

Revision ID: 001
Create Date: 2026-04-09
"""

from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_token',
        sa.Column('user_name', sa.UnicodeText, primary_key=True),
        sa.Column('access_token', sa.UnicodeText),
        sa.Column('token_type', sa.UnicodeText),
        sa.Column('refresh_token', sa.UnicodeText),
        sa.Column('expires_in', sa.UnicodeText),
    )


def downgrade():
    op.drop_table('user_token')
