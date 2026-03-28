"""维修排期预测核心函数"""
import os
import datetime
import pickle
import numpy as np
from typing import List, Dict
from config.algorithm_config import SCHEDULE_MODEL_CONFIG
from order_dispatch.dispatch import smart_dispatch
from database.mysql_oper import get_historical_repair_data


def load_schedule_model():
    """加载排期预测模型（随机森林）"""
    model = None
    try:
        if os.path.exists(SCHEDULE_MODEL_CONFIG["model_path"]):
            with open(SCHEDULE_MODEL_CONFIG["model_path"], "rb") as f:
                model = pickle.load(f)
    except Exception as e:
        print(f"加载排期模型失败: {e}")
    return model


# 全局模型实例
schedule_model = load_schedule_model()


def extract_features(fault_info: dict, dispatch_result: dict, order_location: tuple) -> List[float]:
    """提取排期预测特征"""
    features = []
    for col in SCHEDULE_MODEL_CONFIG["feature_cols"]:
        if col == "fault_type":
            features.append(fault_info["fault_type"])
        elif col == "severity":
            features.append(fault_info["severity"])
        elif col == "worker_id":
            # 将worker_id转换为数值（可预先建立映射表）
            worker_id = dispatch_result.get("worker_id", "W000")
            features.append(int(worker_id.replace("W", "")))
        elif col == "lat":
            features.append(order_location[0])
        elif col == "lng":
            features.append(order_location[1])
    return features


def predict_schedule(img_source, order_id, order_location):
    """
    维修排期预测核心函数
    :param img_source: 故障图片路径/OSS URL
    :param order_id: 工单ID
    :param order_location: 工单位置（纬度，经度）
    :return: 结构化排期结果
    """
    try:
        # 1. 调用派单算法获取故障+派单信息
        dispatch_result = smart_dispatch(img_source, order_id, order_location)
        if dispatch_result["code"] != 200:
            return {
                "code": 400,
                "msg": "派单失败，无法预测排期",
                "data": dispatch_result["data"]
            }

        fault_info = dispatch_result["data"]["fault_info"]
        dispatch_detail = dispatch_result["data"]["dispatch_result"]

        # 2. 提取特征
        features = extract_features(fault_info, dispatch_detail, order_location)

        # 3. 模型预测维修时长（TODO: 替换为实际推理逻辑）
        repair_duration = 0.0
        if schedule_model:
            # repair_duration = schedule_model.predict([features])[0]
            pass
        else:
            # 模拟预测结果
            repair_duration = {
                0: 30,  # 楼道灯损坏
                1: 60,  # 桌椅损坏
                2: 90,  # 健身器材损坏
                3: 120,  # 消防栓损坏
                4: 60,  # 水管漏水
                5: 45,  # 地砖翘起
                6: 90  # 墙面渗水
            }.get(fault_info["fault_type"], 60)

        # 4. 计算截止时间
        now = datetime.datetime.now()
        buffer_time = 10  # 缓冲时间（分钟）
        dead_line = now + datetime.timedelta(minutes=repair_duration + buffer_time)

        # 5. 整合结果
        schedule_result = {
            "repair_duration_min": round(repair_duration, 2),
            "buffer_time_min": buffer_time,
            "dead_line": dead_line.strftime("%Y-%m-%d %H:%M:%S"),
            "predict_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "features": features
        }

        return {
            "code": 200,
            "msg": "排期预测成功",
            "data": {
                "fault_info": fault_info,
                "dispatch_result": dispatch_detail,
                "schedule_result": schedule_result
            }
        }
    except Exception as e:
        print(f"排期预测失败: {e}")
        return {
            "code": 500,
            "msg": f"排期预测失败: {str(e)}",
            "data": {"img_source": img_source, "order_id": order_id}
        }