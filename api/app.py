"""Flask API服务入口"""
from flask import Flask
from flask_cors import CORS
from config.api_config import FLASK_CONFIG, CORS_CONFIG, API_PREFIX
from common.log_utils import init_logger

# 初始化日志
logger = init_logger("api_service")

# 创建Flask应用
app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_CONFIG["secret_key"]

# 配置跨域
CORS(app, resources={f"{API_PREFIX}/*": CORS_CONFIG})

# 全局异常处理
@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception(e,"app_global")
    return {
        "code": 500,
        "msg": f"服务器内部错误: {str(e)}",
        "data": {}
    }, 500

if __name__ == "__main__":
    app.run(
        host=FLASK_CONFIG["host"],
        port=FLASK_CONFIG["port"],
        debug=FLASK_CONFIG["debug"]
    )