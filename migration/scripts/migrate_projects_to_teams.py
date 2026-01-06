"""
Data migration script to migrate existing projects to default teams.
This script should be run after the team models are created but before
the team_id field is made non-nullable (if desired).

Usage:
    python -m alembic_utils run_migration migration/scripts/migrate_projects_to_teams.py
    or manually run via:
    python migration/scripts/migrate_projects_to_teams.py
"""

import uuid
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def migrate_projects_to_teams():
    """
    Migrate existing projects to default teams:
    1. For each user, create a default personal team
    2. Link all projects created by that user to their team
    3. Add user as team owner
    """
    try:
        print("Starting project to team migration...")
        
        # Get all unique project creators
        creators = db.execute(text("""
            SELECT DISTINCT created_by FROM projects WHERE created_by IS NOT NULL
        """)).fetchall()
        
        total_creators = len(creators)
        processed = 0
        
        for (user_id,) in creators:
            try:
                # Check if user already has a default team
                existing_team = db.execute(text("""
                    SELECT id FROM teams 
                    WHERE created_by = :user_id 
                    AND name = :default_name
                    LIMIT 1
                """), {"user_id": user_id, "default_name": f"Default Team - {user_id}"}).first()
                
                if existing_team:
                    team_id = existing_team[0]
                    print(f"  Using existing default team for user {user_id}")
                else:
                    # Create default team for this user
                    team_id = str(uuid.uuid4())
                    now = datetime.utcnow()
                    
                    db.execute(text("""
                        INSERT INTO teams (id, name, description, created_by, is_active, created_at, updated_at)
                        VALUES (:id, :name, :description, :created_by, :is_active, :created_at, :updated_at)
                    """), {
                        "id": team_id,
                        "name": f"Default Team - {user_id}",
                        "description": "Default team created during migration",
                        "created_by": user_id,
                        "is_active": True,
                        "created_at": now,
                        "updated_at": now
                    })
                    
                    # Add user as team owner
                    team_user_id = str(uuid.uuid4())
                    db.execute(text("""
                        INSERT INTO team_users (id, team_id, user_id, role, status, is_active, created_at, updated_at)
                        VALUES (:id, :team_id, :user_id, :role, :status, :is_active, :created_at, :updated_at)
                    """), {
                        "id": team_user_id,
                        "team_id": team_id,
                        "user_id": user_id,
                        "role": "owner",
                        "status": "active",
                        "is_active": True,
                        "created_at": now,
                        "updated_at": now
                    })
                    
                    print(f"  Created default team {team_id} for user {user_id}")
                
                # Link all projects created by this user to the team
                projects_updated = db.execute(text("""
                    UPDATE projects 
                    SET team_id = :team_id 
                    WHERE created_by = :user_id AND team_id IS NULL
                """), {"team_id": team_id, "user_id": user_id})
                
                rows_updated = projects_updated.rowcount
                if rows_updated > 0:
                    print(f"    Linked {rows_updated} projects to team {team_id}")
                
                processed += 1
                
            except Exception as e:
                print(f"  ERROR processing user {user_id}: {str(e)}")
                db.rollback()
                continue
        
        db.commit()
        print(f"\nMigration complete! Processed {processed}/{total_creators} users")
        
        # Print summary statistics
        team_count = db.execute(text("SELECT COUNT(*) FROM teams")).scalar()
        team_user_count = db.execute(text("SELECT COUNT(*) FROM team_users")).scalar()
        projects_with_team = db.execute(text("SELECT COUNT(*) FROM projects WHERE team_id IS NOT NULL")).scalar()
        projects_without_team = db.execute(text("SELECT COUNT(*) FROM projects WHERE team_id IS NULL")).scalar()
        
        print(f"\nMigration Summary:")
        print(f"  Total teams created: {team_count}")
        print(f"  Total team memberships: {team_user_count}")
        print(f"  Projects assigned to teams: {projects_with_team}")
        print(f"  Projects without teams: {projects_without_team}")
        
    except Exception as e:
        print(f"FATAL ERROR: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_projects_to_teams()
