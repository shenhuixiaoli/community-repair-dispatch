# API模块初始化
from .app import app
from .fault_api import register_fault_routes
from .dispatch_api import register_dispatch_routes
from .schedule_api import register_schedule_routes
from .all_api import register_all_routes

# 注册所有路由
register_fault_routes(app)
register_dispatch_routes(app)
register_schedule_routes(app)
register_all_routes(app)

__all__ = ["app"]