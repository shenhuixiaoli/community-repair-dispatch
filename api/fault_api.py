"""故障识别API"""
from flask import Blueprint, request, jsonify
from config.api_config import API_PREFIX
from fault_recognize.predict import predict_fault
from common.data_process import standardize_response, validate_request_params
from common.log_aspect import log_aspect
# 创建蓝图
fault_bp = Blueprint("fault", __name__, url_prefix=f"{API_PREFIX}/fault")


def register_fault_routes(app):
    """注册故障识别路由"""
    app.register_blueprint(fault_bp)


@fault_bp.route("/predict", methods=["POST"])
@log_aspect
def fault_predict():
    """故障识别API接口"""
    try:
        # 获取请求参数
        params = request.json or {}
        # 验证参数
        is_valid, msg = validate_request_params(params, ["img_url"])
        if not is_valid:
            return jsonify(standardize_response(400, msg))

        # 执行故障识别
        result = predict_fault(params["img_url"])

        # 返回结果
        if result["is_valid"]:
            return jsonify(standardize_response(200, "故障识别成功", result))
        else:
            return jsonify(standardize_response(400, "故障识别失败", result))
    except Exception as e:
        return jsonify(standardize_response(500, f"故障识别异常: {str(e)}"))