"""日志配置公共函数"""
import logging
import os
import traceback
from datetime import datetime


def init_logger(log_name: str = "community_algorithm", log_level=logging.INFO):
    """
    初始化日志配置
    :param log_name: 日志名称
    :param log_level: 日志级别
    :return: logger实例
    """
    # 创建日志目录
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 日志文件名
    log_file = os.path.join(log_dir, f"{log_name}_{datetime.now().strftime('%Y%m%d')}.log")

    # 配置logger
    logger = logging.getLogger(log_name)
    logger.setLevel(log_level)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 文件handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(log_level)

    # 控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 添加handler
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# 全局日志实例
logger = init_logger()

# 封装异常打印函数（输出完整堆栈）
def log_exception(e: Exception, module: str):
    """
    打印详细异常信息
    :param e: 异常对象
    :param module: 模块名称（如fault_api/predict）
    """
    logger.error(
        f"【{module}】异常详情:\n"
        f"异常类型: {type(e).__name__}\n"
        f"异常信息: {str(e)}\n"
        f"完整堆栈: {traceback.format_exc()}"
    )