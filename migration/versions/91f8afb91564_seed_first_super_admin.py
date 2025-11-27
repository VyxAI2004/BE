"""seed_first_super_admin

Revision ID: 91f8afb91564
Revises: d08d718c9940
Create Date: 2025-11-27 00:40:19.719784

"""
from typing import Sequence, Union
import uuid
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from passlib.context import CryptContext

# revision identifiers, used by Alembic.
revision: str = '91f8afb91564'
down_revision: Union[str, Sequence[str], None] = 'd08d718c9940'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def upgrade() -> None:
    """Seed first Super Admin user if not exists"""
    
    # Get credentials from environment variables
    email = os.getenv("FIRST_SUPERADMIN_EMAIL", "superadmin@example.com")
    password = os.getenv("FIRST_SUPERADMIN_PASSWORD", "1")
    username = os.getenv("FIRST_SUPERADMIN_USERNAME", "superadmin")
    full_name = os.getenv("FIRST_SUPERADMIN_FULLNAME", "Super Administrator")
    
    # Hash password
    password_hash = pwd_context.hash(password)
    
    # Check if super admin already exists
    conn = op.get_bind()
    existing_user = conn.execute(
        sa.text("SELECT id FROM users WHERE email = :email"),
        {"email": email}
    ).fetchone()
    
    if existing_user:
        print(f"Super Admin user with email {email} already exists. Skipping...")
        return
    
    # Get Super Admin role
    super_admin_role = conn.execute(
        sa.text("SELECT id FROM roles WHERE slug = 'super_admin'")
    ).fetchone()
    
    if not super_admin_role:
        print("Super Admin role not found. Please run seed_roles_permissions migration first.")
        return
    
    super_admin_role_id = str(super_admin_role[0])
    
    # Create Super Admin user
    user_id = str(uuid.uuid4())
    op.execute(
        sa.insert(sa.table('users',
            sa.column('id', postgresql.UUID()),
            sa.column('username', sa.String),
            sa.column('email', sa.String),
            sa.column('password_hash', sa.String),
            sa.column('full_name', sa.String),
            sa.column('is_active', sa.Boolean),
            sa.column('created_at', sa.DateTime),
            sa.column('updated_at', sa.DateTime),
        )).values(
            id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            is_active=True,
            created_at=sa.func.now(),
            updated_at=sa.func.now(),
        )
    )
    
    # Assign Super Admin role to user
    user_role_id = str(uuid.uuid4())
    op.execute(
        sa.insert(sa.table('user_roles',
            sa.column('id', postgresql.UUID()),
            sa.column('user_id', postgresql.UUID()),
            sa.column('role_id', postgresql.UUID()),
            sa.column('assigned_at', sa.DateTime),
            sa.column('assigned_reason', sa.Text),
            sa.column('created_at', sa.DateTime),
            sa.column('updated_at', sa.DateTime),
        )).values(
            id=user_role_id,
            user_id=user_id,
            role_id=super_admin_role_id,
            assigned_at=sa.func.now(),
            assigned_reason="Initial Super Admin seeded by migration",
            created_at=sa.func.now(),
            updated_at=sa.func.now(),
        )
    )
    
    print(f"Super Admin user created successfully!")
    print(f"Email: {email}")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print(f"Please change the password after first login!")


def downgrade() -> None:
    """Remove seeded Super Admin user"""
    
    email = os.getenv("FIRST_SUPERADMIN_EMAIL", "superadmin@example.com")
    
    # Delete user_roles for this user
    op.execute(sa.text("""
        DELETE FROM user_roles 
        WHERE user_id IN (
            SELECT id FROM users WHERE email = :email
        )
    """), {"email": email})
    
    # Delete user
    op.execute(sa.text("""
        DELETE FROM users WHERE email = :email
    """), {"email": email})
    
    print(f"Super Admin user with email {email} removed.")
