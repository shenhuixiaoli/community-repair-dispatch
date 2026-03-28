import numpy as np
import random
from geopy.distance import geodesic  # 计算经纬度距离（米）
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import warnings

warnings.filterwarnings('ignore')

# ===================== 配置项（可根据业务场景调整） =====================
# 多目标权重分配（总和为1，业务导向：紧急程度匹配>技能匹配>响应时间>负载>路程）
WEIGHTS = {
    "skill_match": 0.35,  # 技能匹配度权重（最高，避免派错人）
    "urgency_match": 0.25,  # 紧急程度响应匹配度权重（高紧急优先）
    "response_time": 0.20,  # 响应时间权重
    "load_balance": 0.10,  # 负载均衡权重
    "distance": 0.10  # 路程成本权重
}

# 紧急程度响应时间要求（单位：分钟）
URGENCY_TIME_LIMIT = {
    0: float('inf'),  # 低紧急（0）：无时间限制
    1: 24 * 60,  # 中紧急（1）：24小时内（1440分钟）
    2: 120  # 高紧急（2）：2小时内（120分钟）
}

# 故障类型-维修技能标签映射（与二级模型故障分类一一对应）
FAULT_TYPE_TO_SKILL = {
    0: "electrician",  # 0：楼道灯损坏 → 电工
    1: "repairman",  # 1：桌椅损坏 → 普通维修工
    2: "repairman",  # 2：健身器材损坏 → 普通维修工
    3: "fireman",  # 3：消防栓损坏 → 消防维保人员
    4: "plumber",  # 4：水管漏水 → 水工
    5: "repairman",  # 5：地砖翘起 → 普通维修工
    6: "plumber"  # 6：墙面渗水 → 水工
}

# 维修人员基础参数（可从数据库/Redis中读取实时数据）
DEFAULT_WORKER_SPEED = 50  # 人员移动速度：50米/分钟（社区内步行/电动车）
DEFAULT_BASE_LOAD = 0  # 人员初始负载（待处理工单数量）


# ===================== 数据结构定义（面向对象，适配系统集成） =====================
@dataclass
class WorkOrder:
    """工单类：解析二级模型输出，存储工单核心特征"""
    order_id: str  # 工单ID
    fault_label: str  # 二级模型输出标签（如y_2_1_0）
    location: Tuple[float, float]  # 工单位置（纬度，经度）
    create_time: str = field(default="2026-03-08 10:00:00")  # 工单创建时间
    # 解析后的特征（自动生成）
    fault_type: int = field(init=False)  # 故障类型（0-6）
    severity: int = field(init=False)  # 严重程度（0-2）
    urgency: int = field(init=False)  # 紧急程度（0-2）
    required_skill: str = field(init=False)  # 所需技能标签
    time_limit: float = field(init=False)  # 响应时间限制（分钟）

    def __post_init__(self):
        """初始化时解析故障标签，生成工单特征"""
        if not self.fault_label.startswith('y_'):
            raise ValueError(f"无效故障标签：{self.fault_label}，仅支持有故障标签（y_*_*_*）")
        # 解析标签：y_故障类型_严重程度_紧急程度
        parts = self.fault_label.split('_')[1:]
        if len(parts) != 3:
            raise ValueError(f"故障标签格式错误：{self.fault_label}，正确格式：y_故障类型_严重程度_紧急程度")
        self.fault_type = int(parts[0])
        self.severity = int(parts[1])
        self.urgency = int(parts[2])
        # 匹配所需技能
        self.required_skill = FAULT_TYPE_TO_SKILL.get(self.fault_type, "repairman")
        # 匹配响应时间限制
        self.time_limit = URGENCY_TIME_LIMIT.get(self.urgency, float('inf'))


@dataclass
class RepairWorker:
    """维修人员类：存储人员实时状态，支持动态更新"""
    worker_id: str  # 人员ID
    name: str  # 人员姓名
    skills: List[str]  # 掌握技能标签（如["electrician", "repairman"]）
    location: Tuple[float, float]  # 实时位置（纬度，经度）
    load: int = DEFAULT_BASE_LOAD  # 实时负载（待处理工单数量）
    speed: int = DEFAULT_WORKER_SPEED  # 移动速度（米/分钟）
    is_available: bool = True  # 是否可用（是否在忙）

    def update_load(self, delta: int):
        """更新负载：delta=1（新增工单），delta=-1（完成工单）"""
        self.load = max(0, self.load + delta)

    def update_location(self, new_location: Tuple[float, float]):
        """更新实时位置"""
        self.location = new_location

    def has_skill(self, skill: str) -> bool:
        """判断是否掌握指定技能"""
        return skill in self.skills


@dataclass
class DispatchResult:
    """派单结果类：标准化输出，方便对接后端/工作流"""
    order_id: str  # 工单ID
    worker_id: str  # 派单人员ID
    worker_name: str  # 派单人员姓名
    comprehensive_score: float  # 多目标综合评分（0-1，越高越优）
    # 各目标指标详情
    detail: Dict[str, float] = field(default_factory=dict)
    is_feasible: bool = True  # 是否可行（是否满足所有约束）
    reason: str = field(default="派单成功")  # 失败原因（若不可行）


# ===================== 工具函数：指标计算（多目标基础） =====================
def calculate_geodistance(loc1: Tuple[float, float], loc2: Tuple[float, float]) -> float:
    """计算两个经纬度之间的实际距离（单位：米）"""
    return geodesic(loc1, loc2).meters


def calculate_response_time(distance: float, speed: int) -> float:
    """计算响应时间（单位：分钟）：时间=距离/速度"""
    return distance / speed if speed > 0 else float('inf')


def normalize_value(value: float, min_val: float, max_val: float, reverse: bool = False) -> float:
    """数据归一化（0-1）：reverse=True表示值越小越优（如距离、时间）"""
    if max_val == min_val:
        return 1.0
    norm = (value - min_val) / (max_val - min_val)
    return 1 - norm if reverse else norm


# ===================== 核心算法1：加权贪心算法（实时派单，核心） =====================
class WeightedGreedyDispatch:
    """加权贪心算法：单工单实时派单，选择综合评分最高的可行人员"""

    def __init__(self, workers: List[RepairWorker]):
        self.workers = workers  # 维修人员列表
        self.worker_metrics = {}  # 人员指标缓存

    def calculate_single_worker_score(self, worker: RepairWorker, order: WorkOrder) -> Tuple[float, Dict]:
        """计算单个人员对工单的综合评分及各指标详情"""
        if not worker.is_available:
            return 0.0, {"reason": "人员不可用"}
        if not worker.has_skill(order.required_skill):
            return 0.0, {"reason": "技能不匹配"}

        # 1. 计算基础指标
        distance = calculate_geodistance(worker.location, order.location)  # 距离（米）
        response_time = calculate_response_time(distance, worker.speed)  # 响应时间（分钟）
        load = worker.load  # 人员负载
        skill_match = 1.0 if worker.has_skill(order.required_skill) else 0.0  # 技能匹配度（0/1）
        # 紧急程度匹配度：1=满足时间限制，0=不满足
        urgency_match = 1.0 if response_time <= order.time_limit else 0.0

        # 2. 归一化所有指标（基于当前人员池的极值，保证公平性）
        all_distances = [calculate_geodistance(w.location, order.location) for w in self.workers if w.is_available]
        all_response_times = [calculate_response_time(d, w.speed) for d, w in zip(all_distances, self.workers) if
                              w.is_available]
        all_loads = [w.load for w in self.workers if w.is_available]

        norm_distance = normalize_value(distance, min(all_distances), max(all_distances), reverse=True)
        norm_response_time = normalize_value(response_time, min(all_response_times), max(all_response_times),
                                             reverse=True)
        norm_load = normalize_value(load, min(all_loads), max(all_loads), reverse=True)

        # 3. 计算综合评分（加权求和）
        comprehensive_score = (
                WEIGHTS["skill_match"] * skill_match
                + WEIGHTS["urgency_match"] * urgency_match
                + WEIGHTS["response_time"] * norm_response_time
                + WEIGHTS["load_balance"] * norm_load
                + WEIGHTS["distance"] * norm_distance
        )

        # 4. 指标详情（保留原始值+归一化值）
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

        return round(comprehensive_score, 4), detail

    def dispatch(self, order: WorkOrder) -> DispatchResult:
        """执行派单：返回最优结果"""
        # 过滤可行人员（可用+技能匹配）
        feasible_workers = [w for w in self.workers if w.is_available and w.has_skill(order.required_skill)]
        if not feasible_workers:
            return DispatchResult(
                order_id=order.order_id,
                worker_id="",
                worker_name="",
                comprehensive_score=0.0,
                is_feasible=False,
                reason="无可行维修人员（无可用/技能不匹配）"
            )

        # 计算所有可行人员的评分
        worker_scores = []
        for worker in feasible_workers:
            score, detail = self.calculate_single_worker_score(worker, order)
            worker_scores.append((worker, score, detail))

        # 选择评分最高的人员
        worker_scores.sort(key=lambda x: x[1], reverse=True)
        best_worker, best_score, best_detail = worker_scores[0]

        # 检查是否满足紧急程度时间限制（即使评分高，不满足则标记为不可行）
        if best_detail["response_time_min"] > order.time_limit:
            return DispatchResult(
                order_id=order.order_id,
                worker_id=best_worker.worker_id,
                worker_name=best_worker.name,
                comprehensive_score=best_score,
                detail=best_detail,
                is_feasible=False,
                reason=f"超出{URGENCY_TIME_LIMIT[order.urgency] / 60}小时响应时间限制"
            )

        # 派单成功，返回结果
        return DispatchResult(
            order_id=order.order_id,
            worker_id=best_worker.worker_id,
            worker_name=best_worker.name,
            comprehensive_score=best_score,
            detail=best_detail,
            is_feasible=True,
            reason="派单成功"
        )


# ===================== 进阶算法2：粒子群算法（PSO）（批量派单，全局寻优） =====================
class PSODispatch:
    """粒子群算法：多工单批量派单，全局优化多目标综合评分"""

    def __init__(
            self,
            workers: List[RepairWorker],
            num_particles: int = 50,  # 粒子数量
            max_iter: int = 100,  # 最大迭代次数
            c1: float = 2.0,  # 个体学习因子
            c2: float = 2.0,  # 全局学习因子
            w: float = 0.729  # 惯性权重
    ):
        self.workers = workers
        self.worker_ids = [w.worker_id for w in workers]
        self.num_workers = len(workers)
        # PSO参数
        self.num_particles = num_particles
        self.max_iter = max_iter
        self.c1 = c1
        self.c2 = c2
        self.w = w
        self.r1 = random.random
        self.r2 = random.random

    def _get_feasible_workers_idx(self, order: WorkOrder) -> List[int]:
        """获取单个工单的可行人员索引（技能匹配+可用）"""
        return [
            idx for idx, worker in enumerate(self.workers)
            if worker.is_available and worker.has_skill(order.required_skill)
        ]

    def _init_particle(self, orders: List[WorkOrder]) -> np.ndarray:
        """初始化粒子：仅从可行人员中随机分配，保证技能匹配"""
        particle = np.zeros(len(orders), dtype=int)
        for idx, order in enumerate(orders):
            feasible_idx = self._get_feasible_workers_idx(order)
            if not feasible_idx:
                particle[idx] = -1  # 标记无可行人员
            else:
                particle[idx] = random.choice(feasible_idx)
        return particle

    def _calculate_fitness(self, particle: np.ndarray, orders: List[WorkOrder]) -> float:
        """计算粒子适应度（综合评分，越高越优）：所有可行工单的平均综合评分"""
        total_score = 0.0
        feasible_count = 0
        # 初始化批量负载（基于人员当前负载）
        worker_load = {w.worker_id: w.load for w in self.workers}

        for idx, order in enumerate(orders):
            worker_idx = particle[idx]
            # 跳过无可行人员的工单
            if worker_idx == -1:
                continue
            worker = self.workers[worker_idx]

            # 基础指标计算
            distance = calculate_geodistance(worker.location, order.location)
            response_time = calculate_response_time(distance, worker.speed)
            urgency_match = 1.0 if response_time <= order.time_limit else 0.0
            skill_match = 1.0  # 粒子初始化已保证技能匹配

            # 归一化指标（基于批量场景的极值）
            # 负载归一化：考虑批量派单后的负载
            current_load = worker_load[worker.worker_id]
            norm_load = normalize_value(current_load, 0, len(orders), reverse=True)
            # 响应时间归一化：基于工单时间限制
            norm_response_time = normalize_value(response_time, 0, order.time_limit + 100, reverse=True)
            # 距离归一化：社区最大距离5000米
            norm_distance = normalize_value(distance, 0, 5000, reverse=True)

            # 综合评分
            score = (
                    WEIGHTS["skill_match"] * skill_match
                    + WEIGHTS["urgency_match"] * urgency_match
                    + WEIGHTS["response_time"] * norm_response_time
                    + WEIGHTS["load_balance"] * norm_load
                    + WEIGHTS["distance"] * norm_distance
            )

            total_score += score
            feasible_count += 1
            # 更新批量负载（模拟派单后的负载）
            worker_load[worker.worker_id] += 1

        # 适应度=平均评分（无可行方案则为0）
        return total_score / feasible_count if feasible_count > 0 else 0.0

    def _clip_particle(self, particle: np.ndarray, orders: List[WorkOrder]) -> np.ndarray:
        """裁剪粒子：确保所有工单都分配给可行人员"""
        for idx, order in enumerate(orders):
            feasible_idx = self._get_feasible_workers_idx(order)
            if not feasible_idx:
                particle[idx] = -1
            elif particle[idx] not in feasible_idx:
                particle[idx] = random.choice(feasible_idx)
        return particle

    def dispatch_batch(self, orders: List[WorkOrder]) -> List[DispatchResult]:
        """批量派单：输入工单列表，返回每个工单的派单结果"""
        num_orders = len(orders)
        if num_orders == 0:
            raise ValueError("工单列表不能为空")
        if self.num_workers == 0:
            return [DispatchResult(
                order_id=o.order_id,
                worker_id="",
                worker_name="",
                comprehensive_score=0.0,
                is_feasible=False,
                reason="无维修人员"
            ) for o in orders]

        # 1. 初始化粒子群（仅包含可行解）
        particles = [self._init_particle(orders) for _ in range(self.num_particles)]
        velocities = [np.zeros(num_orders) for _ in range(self.num_particles)]

        # 2. 初始化个体最优和全局最优
        p_best = []
        for p in particles:
            fitness = self._calculate_fitness(p, orders)
            p_best.append((p.copy(), fitness))

        # 全局最优（初始）
        g_best = max(p_best, key=lambda x: x[1])

        # 3. 迭代寻优
        for iter in range(self.max_iter):
            for i in range(self.num_particles):
                particle, fitness = p_best[i]
                # 更新速度
                velocities[i] = (
                        self.w * velocities[i]
                        + self.c1 * self.r1() * (p_best[i][0] - particle)
                        + self.c2 * self.r2() * (g_best[0] - particle)
                )
                # 更新粒子并裁剪到可行解空间
                new_particle = np.around(particle + velocities[i]).astype(int)
                new_particle = self._clip_particle(new_particle, orders)

                # 计算新适应度
                new_fitness = self._calculate_fitness(new_particle, orders)

                # 更新个体最优
                if new_fitness > fitness:
                    p_best[i] = (new_particle.copy(), new_fitness)

                # 更新全局最优
                if new_fitness > g_best[1]:
                    g_best = (new_particle.copy(), new_fitness)

            # 打印迭代日志
            if (iter + 1) % 20 == 0:
                print(f"PSO迭代{iter + 1}/{self.max_iter}，当前全局最优适应度：{g_best[1]:.4f}")

        # 4. 解析全局最优粒子，生成派单结果
        best_scheme = g_best[0]
        results = []
        greedy = WeightedGreedyDispatch(self.workers)  # 复用贪心算法计算指标详情

        for idx, order in enumerate(orders):
            worker_idx = best_scheme[idx]
            # 处理无可行人员的情况
            if worker_idx == -1:
                results.append(DispatchResult(
                    order_id=order.order_id,
                    worker_id="",
                    worker_name="",
                    comprehensive_score=0.0,
                    is_feasible=False,
                    reason="无可行维修人员（技能不匹配/人员不可用）"
                ))
                continue

            worker = self.workers[worker_idx]
            # 计算单工单指标详情
            score, detail = greedy.calculate_single_worker_score(worker, order)

            # 校验可行性
            is_feasible = True
            reason = "派单成功"
            if not worker.is_available or not worker.has_skill(order.required_skill):
                is_feasible = False
                reason = "技能不匹配/人员不可用"
            elif detail["response_time_min"] > order.time_limit:
                is_feasible = False
                reason = f"超出{URGENCY_TIME_LIMIT[order.urgency] / 60}小时响应时间限制"

            # 生成结果
            results.append(DispatchResult(
                order_id=order.order_id,
                worker_id=worker.worker_id,
                worker_name=worker.name,
                comprehensive_score=score,
                detail=detail,
                is_feasible=is_feasible,
                reason=reason
            ))

        return results


# ===================== 算法测试与使用示例 =====================
def test_dispatch_algorithm():
    """测试派单算法：单工单贪心派单 + 多工单PSO批量派单"""
    # 1. 初始化维修人员（模拟社区真实人员，可从数据库读取）
    workers = [
        RepairWorker(
            worker_id="W001",
            name="张三",
            skills=["electrician"],
            location=(31.2304, 121.4737),  # 上海经纬度（示例）
            load=1,
            speed=60
        ),
        RepairWorker(
            worker_id="W002",
            name="李四",
            skills=["plumber"],
            location=(31.2305, 121.4738),
            load=0,
            speed=50
        ),
        RepairWorker(
            worker_id="W003",
            name="王五",
            skills=["repairman"],
            location=(31.2306, 121.4739),
            load=2,
            speed=40
        ),
        RepairWorker(
            worker_id="W004",
            name="赵六",
            skills=["fireman", "repairman"],
            location=(31.2307, 121.4740),
            load=0,
            speed=50
        )
    ]

    # 2. 初始化工单（二级模型输出标签示例）
    # 工单1：健身器材损坏（2）、中度（1）、低紧急（0）→ y_2_1_0
    order1 = WorkOrder(
        order_id="O001",
        fault_label="y_2_1_0",
        location=(31.2306, 121.4739)
    )
    # 工单2：水管漏水（4）、严重（2）、高紧急（2）→ y_4_2_2
    order2 = WorkOrder(
        order_id="O002",
        fault_label="y_4_2_2",
        location=(31.2305, 121.4738)
    )
    # 工单3：消防栓损坏（3）、中度（1）、中紧急（1）→ y_3_1_1
    order3 = WorkOrder(
        order_id="O003",
        fault_label="y_3_1_1",
        location=(31.2307, 121.4740)
    )

    # 3. 测试核心：加权贪心算法（单工单）
    print("=" * 80)
    print("【加权贪心算法 - 单工单派单测试】")
    print("=" * 80)
    greedy_dispatch = WeightedGreedyDispatch(workers)
    res1 = greedy_dispatch.dispatch(order1)
    res2 = greedy_dispatch.dispatch(order2)
    for res in [res1, res2]:
        print(f"工单ID：{res.order_id}")
        print(f"派单人员：{res.worker_name}（{res.worker_id}）")
        print(f"综合评分：{res.comprehensive_score}")
        print(f"派单状态：{'成功' if res.is_feasible else '失败'} - {res.reason}")
        print(f"指标详情：{res.detail}")
        print("-" * 60)

    # 4. 测试进阶：粒子群算法（多工单批量）
    print("=" * 80)
    print("【粒子群算法 - 多工单批量派单测试】")
    print("=" * 80)
    pso_dispatch = PSODispatch(workers, num_particles=30, max_iter=80)
    batch_res = pso_dispatch.dispatch_batch([order1, order2, order3])
    for res in batch_res:
        print(f"工单ID：{res.order_id}")
        print(f"派单人员：{res.worker_name}（{res.worker_id}）")
        print(f"综合评分：{res.comprehensive_score}")
        print(f"派单状态：{'成功' if res.is_feasible else '失败'} - {res.reason}")
        print("-" * 60)


if __name__ == "__main__":
    # 执行测试
    test_dispatch_algorithm()