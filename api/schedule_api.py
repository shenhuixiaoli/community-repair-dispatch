"""维修排期预测API"""
from flask import Blueprint, request, jsonify
from config.api_config import API_PREFIX
from repair_schedule.predict import predict_schedule
from common.data_process import standardize_response, validate_request_params
from common.log_aspect import log_aspect
# 创建蓝图
schedule_bp = Blueprint("schedule", __name__, url_prefix=f"{API_PREFIX}/schedule")


def register_schedule_routes(app):
    """注册排期路由"""
    app.register_blueprint(schedule_bp)


@schedule_bp.route("/predict", methods=["POST"])
@log_aspect
def schedule_predict():
    """排期预测API接口"""
    try:
        # 获取请求参数
        params = request.json or {}
        # 验证参数
        required = ["dispatch_result", "order_id", "lat", "lng"]
        is_valid, msg = validate_request_params(params, required)
        if not is_valid:
            return jsonify(standardize_response(400, msg))

        # 转换坐标
        order_location = (float(params["lat"]), float(params["lng"]))

        # 执行排期预测
        result = predict_schedule(
            dispatch_result=params["dispatch_result"],
            order_id=params["order_id"],
            order_location=order_location
        )

        # 返回结果
        return jsonify(standardize_response(result["code"], result["msg"], result["data"]))
    except Exception as e:
        return jsonify(standardize_response(500, f"排期预测异常: {str(e)}"))