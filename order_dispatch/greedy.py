"""加权贪心派单算法核心"""
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from config.algorithm_config import DISPATCH_WEIGHTS, URGENCY_TIME_LIMIT, FAULT_TYPE_TO_SKILL
from order_dispatch.utils import calculate_geodistance, calculate_response_time, normalize_value


@dataclass
class WorkOrder:
    """工单类"""
    order_id: str
    fault_label: str
    location: Tuple[float, float]
    fault_type: int = field(init=False)
    severity: int = field(init=False)
    urgency: int = field(init=False)
    required_skill: str = field(init=False)
    time_limit: float = field(init=False)

    def __post_init__(self):
        """解析标签初始化"""
        from fault_recognize.utils import parse_fault_label
        label_info = parse_fault_label(self.fault_label)
        self.fault_type = label_info["fault_type"]
        self.severity = label_info["severity"]
        self.urgency = label_info["urgency"]
        self.required_skill = FAULT_TYPE_TO_SKILL.get(self.fault_type, "repairman")
        self.time_limit = URGENCY_TIME_LIMIT.get(self.urgency, float('inf'))


@dataclass
class RepairWorker:
    """维修人员类"""
    worker_id: str
    name: str
    skills: List[str]
    location: Tuple[float, float]
    load: int = 0
    speed: int = 50
    is_available: bool = True

    def update_load(self, delta: int):
        self.load = max(0, self.load + delta)

    def has_skill(self, skill: str) -> bool:
        return skill in self.skills


@dataclass
class DispatchResult:
    """派单结果类"""
    order_id: str
    worker_id: str
    worker_name: str
    comprehensive_score: float
    detail: Dict[str, float] = field(default_factory=dict)
    is_feasible: bool = True
    reason: str = "派单成功"


class WeightedGreedyDispatch:
    """加权贪心派单算法"""

    def __init__(self, workers: List[RepairWorker]):
        self.workers = workers

    def calculate_single_worker_score(self, worker: RepairWorker, order: WorkOrder) -> Tuple[float, Dict]:
        """计算单个人员评分"""
        if not worker.is_available or not worker.has_skill(order.required_skill):
            return 0.0, {"reason": "人员不可用/技能不匹配"}

        # 计算基础指标
        distance = calculate_geodistance(worker.location, order.location)
        response_time = calculate_response_time(distance, worker.speed)
        load = worker.load
        skill_match = 1.0 if worker.has_skill(order.required_skill) else 0.0
        urgency_match = 1.0 if response_time <= order.time_limit else 0.0

        # 归一化
        all_distances = [calculate_geodistance(w.location, order.location) for w in self.workers if w.is_available]
        all_response_times = [calculate_response_time(d, w.speed) for d, w in zip(all_distances, self.workers) if
                              w.is_available]
        all_loads = [w.load for w in self.workers if w.is_available]

        norm_distance = normalize_value(distance, min(all_distances), max(all_distances), reverse=True)
        norm_response_time = normalize_value(response_time, min(all_response_times), max(all_response_times),
                                             reverse=True)
        norm_load = normalize_value(load, min(all_loads), max(all_loads), reverse=True)

        # 综合评分
        score = (
                DISPATCH_WEIGHTS["skill_match"] * skill_match
                + DISPATCH_WEIGHTS["urgency_match"] * urgency_match
                + DISPATCH_WEIGHTS["response_time"] * norm_response_time
                + DISPATCH_WEIGHTS["load_balance"] * norm_load
                + DISPATCH_WEIGHTS["distance"] * norm_distance
        )

        # 详情
        detail = {
            "skill_match": round(skill_match, 4),
            "urgency_match": round(urgency_match, 4),
            "distance_m": round(distance, 2),
            "norm_distance": round(norm_distance, 4),
            "response_time_min": round(response_time, 2),
            "norm_response_time": round(norm_response_time, 4),
            "load": load,
            "norm_load": round(norm_load, 4)
        }

        return round(score, 4), detail

    def dispatch(self, order: WorkOrder) -> DispatchResult:
        """执行派单"""
        # 过滤可行人员
        feasible_workers = [w for w in self.workers if w.is_available and w.has_skill(order.required_skill)]
        if not feasible_workers:
            return DispatchResult(
                order_id=order.order_id,
                worker_id="",
                worker_name="",
                comprehensive_score=0.0,
                is_feasible=False,
                reason="无可行维修人员"
            )

        # 计算评分
        worker_scores = []
        for worker in feasible_workers:
            score, detail = self.calculate_single_worker_score(worker, order)
            worker_scores.append((worker, score, detail))

        # 选择最优
        worker_scores.sort(key=lambda x: x[1], reverse=True)
        best_worker, best_score, best_detail = worker_scores[0]

        # 校验时间限制
        if best_detail["response_time_min"] > order.time_limit:
            return DispatchResult(
                order_id=order.order_id,
                worker_id=best_worker.worker_id,
                worker_name=best_worker.name,
                comprehensive_score=best_score,
                detail=best_detail,
                is_feasible=False,
                reason=f"超出{order.time_limit / 60}小时响应时间限制"
            )

        return DispatchResult(
            order_id=order.order_id,
            worker_id=best_worker.worker_id,
            worker_name=best_worker.name,
            comprehensive_score=best_score,
            detail=best_detail
        )