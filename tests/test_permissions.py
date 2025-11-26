import sys
import os
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.getcwd())
os.environ['APP_ENV'] = 'dev'

try:
    from services.sale_smart_ai_app.permission import PermissionService
    from services.sale_smart_ai_app.auth import AuthService
    from services.sale_smart_ai_app.project import ProjectService
    from core.dependencies.auth import verify_token
    from schemas.auth import TokenData

    print("Imports successful.")

    # Mock DB Session
    mock_db = MagicMock()

    # Instantiate services
    perm_service = PermissionService(mock_db)
    auth_service = AuthService(mock_db)
    project_service = ProjectService(mock_db)

    print("Service instantiation successful.")
    
    # Check TokenData schema
    try:
        token_data = TokenData(
            user_id="123e4567-e89b-12d3-a456-426614174000",
            email="test@example.com",
            roles=["admin"],
            exp="2024-01-01T00:00:00",
            iss="sale-smart-ai",
            aud="sale-smart-ai-app",
            jti="unique-id"
        )
        # Ensure no permission fields are required
        print("TokenData schema check successful.")
    except Exception as e:
        print(f"TokenData schema check failed: {e}")

except Exception as e:
    print(f"Verification failed: {e}")
    sys.exit(1)
