"""seed_roles_permissions

Revision ID: d08d718c9940
Revises: seed_roles_permissions
Create Date: 2025-11-02 23:38:42.121956

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd08d718c9940'
down_revision: Union[str, Sequence[str], None] = '699b589a91fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed default system roles and permissions"""
    
    # First, add missing columns to existing tables using raw SQL
    # Check and add columns to roles table
    op.execute("""
        ALTER TABLE roles 
        ADD COLUMN IF NOT EXISTS slug VARCHAR(50) DEFAULT '';
    """)
    op.execute("""
        ALTER TABLE roles 
        ADD COLUMN IF NOT EXISTS is_system_role BOOLEAN NOT NULL DEFAULT false;
    """)
    op.execute("""
        ALTER TABLE roles 
        ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 100;
    """)
    op.execute("""
        ALTER TABLE roles 
        ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;
    """)
    
    # Check and add columns to permissions table
    op.execute("""
        ALTER TABLE permissions 
        ADD COLUMN IF NOT EXISTS slug VARCHAR(100) DEFAULT '';
    """)
    op.execute("""
        ALTER TABLE permissions 
        ADD COLUMN IF NOT EXISTS category VARCHAR(50) NOT NULL DEFAULT 'general';
    """)
    op.execute("""
        ALTER TABLE permissions 
        ADD COLUMN IF NOT EXISTS is_system_permission BOOLEAN NOT NULL DEFAULT false;
    """)
    op.execute("""
        ALTER TABLE permissions 
        ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;
    """)
    
    # Check and add columns to user_roles table
    op.execute("""
        ALTER TABLE user_roles 
        ADD COLUMN IF NOT EXISTS assigned_at VARCHAR(50);
    """)
    op.execute("""
        ALTER TABLE user_roles 
        ADD COLUMN IF NOT EXISTS assigned_reason TEXT;
    """)
    
    # Check and add columns to role_permissions table
    op.execute("""
        ALTER TABLE role_permissions 
        ADD COLUMN IF NOT EXISTS is_explicitly_granted BOOLEAN NOT NULL DEFAULT true;
    """)
    
    # Generate UUIDs for roles and permissions
    super_admin_role_id = str(uuid.uuid4())
    admin_role_id = str(uuid.uuid4())
    user_role_id = str(uuid.uuid4())
    guest_role_id = str(uuid.uuid4())

    # Define permission categories and their permissions
    permissions_data = [
        # User Management
        ("view_users", "view_users", "View users list", "user_management", True),
        ("create_user", "create_user", "Create new user", "user_management", True),
        ("update_user", "update_user", "Update user information", "user_management", True),
        ("delete_user", "delete_user", "Delete user", "user_management", True),
        
        # Role Management
        ("manage_roles", "manage_roles", "Create, update, delete roles", "role_management", True),
        ("assign_roles", "assign_roles", "Assign roles to users", "role_management", True),
        ("view_roles", "view_roles", "View roles and permissions", "role_management", True),
        
        # Project Management
        ("view_all_projects", "view_all_projects", "View all projects in system", "project_management", True),
        ("create_project", "create_project", "Create new project", "project_management", True),
        ("update_project", "update_project", "Update project information", "project_management", True),
        ("delete_any_project", "delete_any_project", "Delete any project", "project_management", True),
        
        # AI Model Management
        ("manage_ai_models", "manage_ai_models", "Create, update, delete AI models", "ai_model_management", True),
        ("view_all_ai_models", "view_all_ai_models", "View all AI models", "ai_model_management", True),
        
        # System Management
        ("view_system_stats", "view_system_stats", "View system statistics", "system_management", True),
        ("manage_system_settings", "manage_system_settings", "Manage system settings", "system_management", True),
    ]
    
    # Define role data with names to check existence
    roles_data_names = [
        ("Super Admin", "super_admin", "System super administrator with all permissions", 1000),
        ("Admin", "admin", "Administrator with most permissions", 500),
        ("User", "user", "Regular user with basic permissions", 100),
        ("Guest", "guest", "Guest user with limited permissions", 1),
    ]

    # Insert permissions - check if not exists
    permission_ids = {}
    for name, slug, description, category, is_system in permissions_data:
        # Check if permission already exists
        existing = op.get_bind().execute(
            sa.text("SELECT id FROM permissions WHERE name = :name"),
            {"name": name}
        ).fetchone()
        
        if existing:
            permission_ids[slug] = str(existing[0])
        else:
            perm_id = str(uuid.uuid4())
            permission_ids[slug] = perm_id
            op.execute(
                sa.insert(sa.table('permissions',
                    sa.column('id', postgresql.UUID()),
                    sa.column('name', sa.String),
                    sa.column('slug', sa.String),
                    sa.column('description', sa.String),
                    sa.column('category', sa.String),
                    sa.column('is_system_permission', sa.Boolean),
                    sa.column('is_active', sa.Boolean),
                    sa.column('created_at', sa.DateTime),
                    sa.column('updated_at', sa.DateTime),
                )).values(
                    id=perm_id,
                    name=name,
                    slug=slug,
                    description=description,
                    category=category,
                    is_system_permission=is_system,
                    is_active=True,
                    created_at=sa.func.now(),
                    updated_at=sa.func.now(),
                )
            )

    # Insert roles - check if not exists
    role_ids = {}
    for name, slug, description, priority in roles_data_names:
        # Check if role already exists
        existing = op.get_bind().execute(
            sa.text("SELECT id FROM roles WHERE name = :name"),
            {"name": name}
        ).fetchone()
        
        if existing:
            role_ids[slug] = str(existing[0])
        else:
            role_id = str(uuid.uuid4())
            role_ids[slug] = role_id
            op.execute(
                sa.insert(sa.table('roles',
                    sa.column('id', postgresql.UUID()),
                    sa.column('name', sa.String),
                    sa.column('slug', sa.String),
                    sa.column('description', sa.String),
                    sa.column('is_system_role', sa.Boolean),
                    sa.column('priority', sa.Integer),
                    sa.column('is_active', sa.Boolean),
                    sa.column('created_at', sa.DateTime),
                    sa.column('updated_at', sa.DateTime),
                )).values(
                    id=role_id,
                    name=name,
                    slug=slug,
                    description=description,
                    is_system_role=True,
                    priority=priority,
                    is_active=True,
                    created_at=sa.func.now(),
                    updated_at=sa.func.now(),
                )
            )

    # Assign permissions to roles
    role_permissions = [
        # Super Admin - all permissions
        ("super_admin", [
            "view_users", "create_user", "update_user", "delete_user",
            "manage_roles", "assign_roles", "view_roles",
            "view_all_projects", "create_project", "update_project", "delete_any_project",
            "manage_ai_models", "view_all_ai_models",
            "view_system_stats", "manage_system_settings"
        ]),
        # Admin - most permissions except system settings
        ("admin", [
            "view_users", "create_user", "update_user", "delete_user",
            "manage_roles", "assign_roles", "view_roles",
            "view_all_projects", "create_project", "update_project", "delete_any_project",
            "manage_ai_models", "view_all_ai_models",
            "view_system_stats",
        ]),
        # User - basic permissions
        ("user", [
            "view_users", "create_project", "view_all_ai_models"
        ]),
        # Guest - minimal permissions
        ("guest", [
            "view_all_ai_models"
        ]),
    ]

    for role_slug, permission_slugs in role_permissions:
        if role_slug in role_ids:
            role_id = role_ids[role_slug]
            for perm_slug in permission_slugs:
                if perm_slug in permission_ids:
                    perm_id = permission_ids[perm_slug]
                    # Check if role_permission already exists
                    existing = op.get_bind().execute(
                        sa.text("SELECT id FROM role_permissions WHERE role_id = :role_id AND permission_id = :perm_id"),
                        {"role_id": role_id, "perm_id": perm_id}
                    ).fetchone()
                    
                    if not existing:
                        rp_id = str(uuid.uuid4())
                        op.execute(
                            sa.insert(sa.table('role_permissions',
                                sa.column('id', postgresql.UUID()),
                                sa.column('role_id', postgresql.UUID()),
                                sa.column('permission_id', postgresql.UUID()),
                                sa.column('is_explicitly_granted', sa.Boolean),
                                sa.column('created_at', sa.DateTime),
                                sa.column('updated_at', sa.DateTime),
                            )).values(
                                id=rp_id,
                                role_id=role_id,
                                permission_id=perm_id,
                                is_explicitly_granted=True,
                                created_at=sa.func.now(),
                                updated_at=sa.func.now(),
                            )
                        )


def downgrade() -> None:
    """Remove seeded roles and permissions"""
    # Delete system role_permissions
    op.execute(sa.text("""
        DELETE FROM role_permissions 
        WHERE role_id IN (
            SELECT id FROM roles WHERE is_system_role = true
        )
    """))
    
    # Delete system roles
    op.execute(sa.text("""
        DELETE FROM roles WHERE is_system_role = true
    """))
    
    # Delete system permissions
    op.execute(sa.text("""
        DELETE FROM permissions WHERE is_system_permission = true
    """))
