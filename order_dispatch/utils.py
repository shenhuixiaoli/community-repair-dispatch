"""派单算法工具函数"""
from typing import Tuple, List

import numpy as np
import math

try:
    from geopy.distance import geodesic  # type: ignore
except Exception:  # geopy 可能未安装，使用haversine兜底
    geodesic = None

def calculate_geodistance(loc1: Tuple[float, float], loc2: Tuple[float, float]) -> float:
    """计算经纬度距离（米）"""
    if geodesic is not None:
        return geodesic(loc1, loc2).meters

    # haversine 公式（地球半径取6371000米）
    lat1, lon1 = loc1
    lat2, lon2 = loc2
    rlat1 = math.radians(lat1)
    rlat2 = math.radians(lat2)
    dlat = rlat2 - rlat1
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return 6371000.0 * c

def calculate_response_time(distance: float, speed: int) -> float:
    """计算响应时间（分钟）"""
    return distance / speed if speed > 0 else float('inf')

def normalize_value(value: float, min_val: float, max_val: float, reverse: bool = False) -> float:
    """数据归一化（0-1）"""
    if max_val == min_val:
        return 1.0
    norm = (value - min_val) / (max_val - min_val)
    return 1 - norm if reverse else norm

def convert_worker_status(redis_data: List[dict]) -> List[dict]:
    """转换Redis人员状态数据格式"""
    converted = []
    for w in redis_data:
        converted.append({
            "worker_id": w.get("worker_id", ""),
            "name": w.get("name", ""),
            "skills": w.get("skills", []),
            "lat": float(w.get("lat", 0.0)),
            "lng": float(w.get("lng", 0.0)),
            "load": int(w.get("load", 0)),
            "speed": int(w.get("speed", 50)),
            "is_available": w.get("is_available", True)
        })
    return converted