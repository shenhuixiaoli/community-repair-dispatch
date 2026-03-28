"""粒子群派单算法核心"""
import numpy as np
import random
from typing import List
from order_dispatch.greedy import WorkOrder, RepairWorker, DispatchResult, WeightedGreedyDispatch
from order_dispatch.utils import calculate_geodistance, calculate_response_time, normalize_value
from config.algorithm_config import DISPATCH_WEIGHTS, URGENCY_TIME_LIMIT


class PSODispatch:
    """粒子群批量派单算法"""

    def __init__(self, workers: List[RepairWorker], num_particles=50, max_iter=100, c1=2.0, c2=2.0, w=0.729):
        self.workers = workers
        self.worker_ids = [w.worker_id for w in workers]
        self.num_workers = len(workers)
        self.num_particles = num_particles
        self.max_iter = max_iter
        self.c1 = c1
        self.c2 = c2
        self.w = w

    def _get_feasible_workers_idx(self, order: WorkOrder) -> List[int]:
        """获取单个工单的可行人员索引（技能匹配+可用）"""
        return [
            idx for idx, worker in enumerate(self.workers)
            if worker.is_available and worker.has_skill(order.required_skill)
        ]

    def _init_particle(self, orders: List[WorkOrder]) -> np.ndarray:
        """
        初始化粒子：每个工单只从可行人员中随机分配
        若无可行人员，则标记为-1
        """
        particle = np.zeros(len(orders), dtype=int)
        for idx, order in enumerate(orders):
            feasible_idx = self._get_feasible_workers_idx(order)
            particle[idx] = random.choice(feasible_idx) if feasible_idx else -1
        return particle

    def _calculate_fitness(self, particle: np.ndarray, orders: List[WorkOrder]) -> float:
        """计算适应度"""
        total_score = 0.0
        feasible_count = 0
        worker_load = {w.worker_id: w.load for w in self.workers}

        for idx, order in enumerate(orders):
            worker_idx = int(particle[idx])
            if worker_idx == -1:
                continue
            worker = self.workers[worker_idx]
            # 这里理论上都可行，但仍做一次保护
            if not worker.is_available or not worker.has_skill(order.required_skill):
                continue

            distance = calculate_geodistance(worker.location, order.location)
            response_time = calculate_response_time(distance, worker.speed)
            urgency_match = 1.0 if response_time <= order.time_limit else 0.0
            skill_match = 1.0  # 初始化/裁剪已保证技能匹配

            norm_load = normalize_value(worker_load[worker.worker_id], 0, len(orders), reverse=True)
            norm_response_time = normalize_value(response_time, 0, order.time_limit + 100, reverse=True)
            norm_distance = normalize_value(distance, 0, 5000, reverse=True)

            score = (
                    DISPATCH_WEIGHTS["skill_match"] * skill_match
                    + DISPATCH_WEIGHTS["urgency_match"] * urgency_match
                    + DISPATCH_WEIGHTS["response_time"] * norm_response_time
                    + DISPATCH_WEIGHTS["load_balance"] * norm_load
                    + DISPATCH_WEIGHTS["distance"] * norm_distance
            )

            total_score += score
            feasible_count += 1
            worker_load[worker.worker_id] += 1

        return total_score / feasible_count if feasible_count > 0 else 0.0

    def _clip_particle(self, particle: np.ndarray, orders: List[WorkOrder]) -> np.ndarray:
        """裁剪粒子：确保每个工单分配给可行人员，否则随机修正；无可行则-1"""
        for idx, order in enumerate(orders):
            feasible_idx = self._get_feasible_workers_idx(order)
            if not feasible_idx:
                particle[idx] = -1
                continue
            if int(particle[idx]) not in feasible_idx:
                particle[idx] = random.choice(feasible_idx)
        return particle

    def dispatch_batch(self, orders: List[WorkOrder]) -> List[DispatchResult]:
        """批量派单"""
        num_orders = len(orders)
        if num_orders == 0 or self.num_workers == 0:
            return [DispatchResult(
                order_id=o.order_id,
                worker_id="",
                worker_name="",
                comprehensive_score=0.0,
                is_feasible=False,
                reason="无工单/无维修人员"
            ) for o in orders]

        # 初始化粒子群
        particles = [self._init_particle(orders) for _ in range(self.num_particles)]
        velocities = [np.zeros(num_orders) for _ in range(self.num_particles)]
        p_best = [(p, self._calculate_fitness(p, orders)) for p in particles]
        g_best = max(p_best, key=lambda x: x[1])

        # 迭代寻优
        for iter in range(self.max_iter):
            for i in range(self.num_particles):
                particle, fitness = p_best[i]
                # 更新速度
                velocities[i] = (
                        self.w * velocities[i]
                        + self.c1 * random.random() * (p_best[i][0] - particle)
                        + self.c2 * random.random() * (g_best[0] - particle)
                )
                # 更新粒子
                new_particle = np.around(particle + velocities[i]).astype(int)
                new_particle = self._clip_particle(new_particle, orders)
                # 计算新适应度
                new_fitness = self._calculate_fitness(new_particle, orders)
                # 更新最优
                if new_fitness > fitness:
                    p_best[i] = (new_particle, new_fitness)
                if new_fitness > g_best[1]:
                    g_best = (new_particle, new_fitness)

            if (iter + 1) % 20 == 0:
                print(f"PSO迭代{iter + 1}/{self.max_iter}，最优适应度：{g_best[1]:.4f}")

        # 生成结果
        best_scheme = g_best[0]
        results = []
        greedy = WeightedGreedyDispatch(self.workers)

        for idx, order in enumerate(orders):
            worker_idx = int(best_scheme[idx])
            if worker_idx == -1:
                results.append(DispatchResult(
                    order_id=order.order_id,
                    worker_id="",
                    worker_name="",
                    comprehensive_score=0.0,
                    detail={},
                    is_feasible=False,
                    reason="无可行维修人员（技能不匹配/人员不可用）"
                ))
                continue

            worker = self.workers[worker_idx]
            score, detail = greedy.calculate_single_worker_score(worker, order)

            is_feasible = True
            reason = "派单成功"
            if not worker.is_available or not worker.has_skill(order.required_skill):
                is_feasible = False
                reason = "技能不匹配/人员不可用"
            elif detail["response_time_min"] > order.time_limit:
                is_feasible = False
                reason = f"超出{URGENCY_TIME_LIMIT[order.urgency] / 60}小时响应时间限制"

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