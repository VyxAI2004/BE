"""Add user settings fields (date_of_birth, language, bio, urls)

Revision ID: f7a8b9c0d1e2
Revises: a1b2c3d4e5f6
Create Date: 2025-12-16 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user settings fields to users table
    op.add_column('users', sa.Column(
        'date_of_birth',
        sa.Date(),
        nullable=True,
        comment='User date of birth'
    ))
    
    op.add_column('users', sa.Column(
        'language',
        sa.String(length=10),
        nullable=True,
        server_default='en',
        comment='User preferred language (ISO 639-1 code)'
    ))
    
    op.add_column('users', sa.Column(
        'bio',
        sa.Text(),
        nullable=True,
        comment='User biography/description'
    ))
    
    op.add_column('users', sa.Column(
        'urls',
        postgresql.JSON(astext_type=sa.Text()),
        nullable=True,
        comment='User URLs (website, social media, etc.) stored as JSON array'
    ))


def downgrade() -> None:
    # Remove user settings fields from users table
    op.drop_column('users', 'urls')
    op.drop_column('users', 'bio')
    op.drop_column('users', 'language')
    op.drop_column('users', 'date_of_birth')
