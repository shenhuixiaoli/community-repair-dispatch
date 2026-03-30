"""智能派单API"""
from flask import Blueprint, request, jsonify
from config.api_config import API_PREFIX
from order_dispatch.dispatch import smart_dispatch
from common.data_process import standardize_response, validate_request_params
from common.log_aspect import log_aspect
# 创建蓝图
dispatch_bp = Blueprint("dispatch", __name__, url_prefix=f"{API_PREFIX}/dispatch")


def register_dispatch_routes(app):
    """注册派单路由"""
    app.register_blueprint(dispatch_bp)


@dispatch_bp.route("/smart", methods=["POST"])
@log_aspect
def smart_dispatch_api():
    """智能派单API接口"""
    try:
        # 获取请求参数
        params = request.json or {}
        # 验证参数
        required = ["fault_info", "order_id", "lat", "lng"]
        is_valid, msg = validate_request_params(params, required)
        if not is_valid:
            return jsonify(standardize_response(400, msg))

        # 转换坐标
        order_location = (float(params["lat"]), float(params["lng"]))
        use_pso = params.get("use_pso", False)
        batch_orders = params.get("batch_orders", None)

        # 执行派单
        result = smart_dispatch(
            fault_info=params["fault_info"],
            order_id=params["order_id"],
            order_location=order_location,
            use_pso=use_pso,
            batch_orders=batch_orders
        )

        # 返回结果
        return jsonify(standardize_response(result["code"], result["msg"], result["data"]))
    except Exception as e:
        return jsonify(standardize_response(500, f"派单异常: {str(e)}"))