"""Redis操作工具"""
import redis
from typing import List, Dict, Any
from config.data_config import REDIS_CONFIG
from common.log_utils import logger

class RedisOper:
    """Redis操作类"""
    def __init__(self):
        self.config = REDIS_CONFIG
        self.client = None

    def connect(self):
        """建立Redis连接"""
        try:
            self.client = redis.Redis(**self.config)
            self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            return False

    def get(self, key: str) -> Any:
        """获取值"""
        if not self.connect():
            return None
        return self.client.get(key)

    def set(self, key: str, value: Any, ex: int = None):
        """设置值"""
        if not self.connect():
            return False
        self.client.set(key, value, ex=ex)
        return True

    def hgetall(self, key: str) -> Dict[str, Any]:
        """获取哈希值"""
        if not self.connect():
            return {}
        return self.client.hgetall(key)

    def lrange(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """获取列表值"""
        if not self.connect():
            return []
        return self.client.lrange(key, start, end)

# 全局实例
redis_oper = RedisOper()

def get_worker_real_time_status() -> List[Dict[str, Any]]:
    """获取维修人员实时状态"""
    try:
        # 从Redis读取人员状态列表
        worker_data = redis_oper.lrange("community:workers:real_time_status")
        # 转换格式
        import json
        workers = [json.loads(w) for w in worker_data]
        return convert_worker_status(workers)
    except Exception as e:
        logger.error(f"获取人员状态失败: {e}")
        return []

def update_worker_load(worker_id: str, delta: int):
    """更新人员负载"""
    try:
        key = f"community:worker:{worker_id}:status"
        status = redis_oper.hgetall(key)
        if status:
            status["load"] = int(status.get("load", 0)) + delta
            redis_oper.hmset(key, status)  # 需确认redis版本支持
            return True
        return False
    except Exception as e:
        logger.error(f"更新人员负载失败: {e}")
        return False

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