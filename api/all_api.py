"""全链路API（故障→派单→排期）"""
from flask import Blueprint, request, jsonify
from config.api_config import API_PREFIX
from repair_schedule.predict import predict_schedule
from common.data_process import standardize_response, validate_request_params

# 创建蓝图
all_bp = Blueprint("all", __name__, url_prefix=f"{API_PREFIX}/all")


def register_all_routes(app):
    """注册全链路路由"""
    app.register_blueprint(all_bp)


@all_bp.route("/process", methods=["POST"])
def all_process():
    """全链路处理API接口"""
    try:
        # 获取请求参数
        params = request.json or {}
        # 验证参数
        required = ["img_url", "order_id", "lat", "lng"]
        is_valid, msg = validate_request_params(params, required)
        if not is_valid:
            return jsonify(standardize_response(400, msg))

        # 转换坐标
        order_location = (float(params["lat"]), float(params["lng"]))

        # 执行全链路处理（排期预测已包含故障识别和派单）
        result = predict_schedule(
            img_source=params["img_url"],
            order_id=params["order_id"],
            order_location=order_location
        )

        # 返回结果
        return jsonify(standardize_response(result["code"], result["msg"], result["data"]))
    except Exception as e:
        return jsonify(standardize_response(500, f"全链路处理异常: {str(e)}"))