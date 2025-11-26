"""
Test script to verify permission middleware changes
"""
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())
os.environ['APP_ENV'] = 'dev'

try:
    # Test imports
    print("Testing imports...")
    from middlewares.permissions import check_global_permissions, check_project_permissions
    from services.sale_smart_ai_app.permission import PermissionService
    from shared.enums import GlobalPermissionEnum, ProjectPermissionEnum
    print("All imports successful")
    
    # Test decorator structure
    print("\nTesting decorator structure...")
    
    # Test that decorators can be instantiated
    @check_global_permissions(GlobalPermissionEnum.VIEW_USERS)
    async def test_global_endpoint():
        return "success"
    
    @check_project_permissions("project_id", ProjectPermissionEnum.VIEW_TASKS)
    async def test_project_endpoint(project_id: str):
        return "success"
    
    print("Decorators can be applied to functions")
    
    # Check decorator metadata is preserved
    assert test_global_endpoint.__name__ == "test_global_endpoint", "Function name not preserved"
    assert test_project_endpoint.__name__ == "test_project_endpoint", "Function name not preserved"
    print("Decorator metadata preserved (functools.wraps works)")
    
    print("\n" + "="*50)
    print("All basic verification tests passed!")
    print("="*50)
    print("\nNext steps:")
    print("1. Test with actual API calls to verify permission checks work")
    print("2. Verify SUPER_ADMIN bypass works")
    print("3. Verify ADMIN needs database permissions")
    print("4. Verify project permissions check project membership")
    
except Exception as e:
    print(f"Verification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
