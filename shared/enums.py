from enum import Enum, auto

class RoleEnum(str, Enum):
    """Vai trò của người dùng trong hệ thống (Global roles)."""
    SUPER_ADMIN = "super_admin"  # Quản trị viên cao cấp nhất
    ADMIN = "admin"             # Quản trị viên
    USER = "user"              # Người dùng thông thường
    GUEST = "guest"            # Khách

class GlobalPermissionEnum(str, Enum):
    """Quyền hạn global trong hệ thống."""
    # User Management
    VIEW_USERS = "view_users"
    CREATE_USER = "create_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    
    # Role Management
    MANAGE_ROLES = "manage_roles"
    ASSIGN_ROLES = "assign_roles"
    
    # Project Management
    VIEW_ALL_PROJECTS = "view_all_projects"
    CREATE_PROJECT = "create_project"
    DELETE_ANY_PROJECT = "delete_any_project"
    
    # AI Model Management
    MANAGE_AI_MODELS = "manage_ai_models"
    VIEW_ALL_AI_MODELS = "view_all_ai_models"
    
    # System Management
    VIEW_SYSTEM_STATS = "view_system_stats"
    MANAGE_SYSTEM_SETTINGS = "manage_system_settings"

class ProjectRoleEnum(str, Enum):
    """Vai trò của người dùng trong một project cụ thể."""
    PROJECT_OWNER = "project_owner"      # Chủ sở hữu project
    PROJECT_ADMIN = "project_admin"      # Quản trị viên project
    PROJECT_MEMBER = "project_member"    # Thành viên project
    PROJECT_VIEWER = "project_viewer"    # Người xem project

class ProjectPermissionEnum(str, Enum):
    """Quyền hạn trong một project cụ thể."""
    # Project Settings
    VIEW_PROJECT = "view_project"
    EDIT_PROJECT = "edit_project"
    DELETE_PROJECT = "delete_project"
    
    # Member Management
    INVITE_MEMBERS = "invite_members"
    REMOVE_MEMBERS = "remove_members"
    ASSIGN_ROLES = "assign_roles"
    
    # Product Source Management
    MANAGE_SOURCES = "manage_sources"
    VIEW_SOURCES = "view_sources"
    
    # Crawling Operations
    START_CRAWL = "start_crawl"
    STOP_CRAWL = "stop_crawl"
    VIEW_CRAWL_HISTORY = "view_crawl_history"
    
    # Task Management
    CREATE_TASK = "create_task"
    EDIT_TASK = "edit_task"
    DELETE_TASK = "delete_task"
    ASSIGN_TASK = "assign_task"
    VIEW_TASKS = "view_tasks"
    
    # AI Model Usage
    ASSIGN_AI_MODEL = "assign_ai_model"
    VIEW_AI_RESULTS = "view_ai_results"
    
    # Analytics & Reporting
    VIEW_ANALYTICS = "view_analytics"
    EXPORT_DATA = "export_data"

class ProjectStatusEnum(str, Enum):
    """Trạng thái của Project."""
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class PipelineTypeEnum(str, Enum):
    """Loại quy trình (pipeline) của Project."""
    STANDARD = "standard"
    ADVANCED = "advanced"
    CUSTOM = "custom"

class ScheduleEnum(str, Enum):
    """Tần suất crawl."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"

class PlatformEnum(str, Enum):
    """Nền tảng thương mại điện tử."""
    SHOPEE = "shopee"
    LAZADA = "lazada"
    TIKI = "tiki"
    AMAZON = "amazon"
    CUSTOM = "custom"

class CrawlStatusEnum(str, Enum):
    """Trạng thái của phiên Crawl."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class CrawlTypeEnum(str, Enum):
    """Loại crawl."""
    INITIAL = "initial"     
    SCHEDULED = "scheduled"   
    MANUAL = "manual"       

class TaskStatusEnum(str, Enum):
    """Trạng thái của Task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    FAILED = "failed"

class TaskPriorityEnum(str, Enum):
    """Mức độ ưu tiên của Task."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class StockStatusEnum(str, Enum):
    """Trạng thái kho hàng (Gợi ý thêm cho price_history)."""
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    PRE_ORDER = "pre_order"

class LogActionEnum(str, Enum):
    """Hành động ghi log."""
    # Auth
    LOGIN = "login"
    LOGOUT = "logout"
    CHANGE_PASSWORD = "change_password"
    
    # User
    CREATE_USER = "create_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    
    # Project
    CREATE_PROJECT = "create_project"
    UPDATE_PROJECT = "update_project"
    DELETE_PROJECT = "delete_project"
    ASSIGN_PROJECT = "assign_project"
    UPDATE_PROJECT_STATUS = "update_project_status"
    
    # Member
    ADD_MEMBER = "add_member"
    REMOVE_MEMBER = "remove_member"
    
    # System
    SYSTEM_ERROR = "system_error"