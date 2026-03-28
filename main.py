"""项目启动入口"""
from api.app import app
from config.api_config import FLASK_CONFIG
from common.log_utils import init_logger

# 初始化全局日志
logger = init_logger("community_algorithm_service")

if __name__ == "__main__":
    logger.info("启动智能社区算法服务...")
    logger.info(f"服务地址: http://{FLASK_CONFIG['host']}:{FLASK_CONFIG['port']}")
    # 启动Flask服务
    app.run(
        host=FLASK_CONFIG["host"],
        port=FLASK_CONFIG["port"],
        debug=FLASK_CONFIG["debug"],
        threaded=True  # 开启多线程
    )