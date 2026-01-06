"""Add Team and TeamUser tables

Revision ID: k4l5m6n7o8p9
Revises: 2024_01_04_1
Create Date: 2026-01-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'k4l5m6n7o8p9'
down_revision: Union[str, Sequence[str], None] = '2024_01_04_1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create teams table
    op.create_table(
        'teams',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create team_users table
    op.create_table(
        'team_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('team_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(length=20), server_default='member', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('invited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_team_users_team_id', 'team_id'),
        sa.Index('ix_team_users_user_id', 'user_id')
    )
    
    # Add team_id and visibility to projects table
    op.add_column('projects', sa.Column('team_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('projects', sa.Column('visibility', sa.String(length=20), server_default='public', nullable=False))
    
    # Create index for team_id
    op.create_index('ix_projects_team_id', 'projects', ['team_id'])
    
    # Add foreign key constraint for team_id
    op.create_foreign_key(
        'fk_projects_team_id',
        'projects',
        'teams',
        ['team_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Drop foreign key
    op.drop_constraint('fk_projects_team_id', 'projects', type_='foreignkey')
    
    # Drop index
    op.drop_index('ix_projects_team_id', 'projects')
    
    # Drop columns from projects
    op.drop_column('projects', 'visibility')
    op.drop_column('projects', 'team_id')
    
    # Drop team_users table
    op.drop_table('team_users')
    
    # Drop teams table
    op.drop_table('teams')
