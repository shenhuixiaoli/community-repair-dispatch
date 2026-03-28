"""数据处理公共函数"""
import pandas as pd
from typing import Dict, Any, List


def standardize_response(code: int, msg: str, data: Any = None) -> Dict[str, Any]:
    """
    标准化API响应格式
    :param code: 状态码（200成功，400参数错误，500服务器错误）
    :param msg: 提示信息
    :param data: 业务数据
    :return: 标准化字典
    """
    return {
        "code": code,
        "msg": msg,
        "data": data if data is not None else {},
        "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")  # 需import pandas as pd
    }

def validate_request_params(params: Dict[str, Any], required: List[str]) -> tuple:
    """
    验证请求参数
    :param params: 请求参数字典
    :param required: 必选参数列表
    :return: (是否有效, 错误信息)
    """
    missing = [p for p in required if p not in params or params[p] is None]
    if missing:
        return False, f"缺失必选参数: {', '.join(missing)}"
    return True, ""