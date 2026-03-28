import time
import json
from functools import wraps
from flask import request, jsonify

def log_aspect(func):
    """
    真正的 AOP 切面装饰器
    作用：自动打印所有接口的 请求/响应 日志
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # ========== 1. 请求前日志（AOP前置通知） ==========
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        api_path = request.path
        params = request.json or {}
        params_str = json.dumps(params, ensure_ascii=False)
        print(f"[{now}] 接收请求 {api_path} | 参数：{params_str}")

        try:
            # ========== 2. 执行原接口逻辑 ==========
            response = func(*args, **kwargs)

            # ========== 3. 响应后日志（AOP后置通知） ==========
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            resp_data = response.get_json() if hasattr(response, 'get_json') else {}
            resp_str = json.dumps(resp_data, ensure_ascii=False)
            print(f"[{now}] 响应请求 {api_path} | 返回：{resp_str}")

            return response

        except Exception as e:
            # ========== 4. 异常日志（AOP异常通知） ==========
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            error_msg = f"接口异常：{str(e)}"
            print(f"[{now}] 异常请求 {api_path} | 错误：{error_msg}")
            raise

    return wrapper