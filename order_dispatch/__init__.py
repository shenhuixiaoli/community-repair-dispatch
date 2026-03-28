# 派单算法模块初始化
from .greedy import WeightedGreedyDispatch
from .pso import PSODispatch
from .dispatch import smart_dispatch

__all__ = ["WeightedGreedyDispatch", "PSODispatch", "smart_dispatch"]

# order_dispatch/__init__.py
from .dispatch_core import (
    WorkOrder,
    RepairWorker,
    DispatchResult,
    WeightedGreedyDispatch,
    PSODispatch
)

# 封装单工单派单接口
def dispatch_single_order(workers: list[RepairWorker], order: WorkOrder) -> DispatchResult:
    """单工单派单接口（贪心算法）"""
    dispatch = WeightedGreedyDispatch(workers)
    return dispatch.dispatch(order)

# 封装批量派单接口
def dispatch_batch_orders(workers: list[RepairWorker], orders: list[WorkOrder]) -> list[DispatchResult]:
    """批量工单派单接口（PSO算法）"""
    dispatch = PSODispatch(workers)
    return dispatch.dispatch_batch(orders)

def save_dispatch_result(result: DispatchResult):
    """保存派单结果到数据库"""
    import pymysql
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="your_password",
        db="community_algorithm"
    )
    cursor = conn.cursor()
    sql = """
    INSERT INTO dispatch_results (order_id, worker_id, worker_name, comprehensive_score, is_feasible, reason)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    cursor.execute(sql, (
        result.order_id,
        result.worker_id,
        result.worker_name,
        result.comprehensive_score,
        result.is_feasible,
        result.reason
    ))
    conn.commit()
    cursor.close()
    conn.close()