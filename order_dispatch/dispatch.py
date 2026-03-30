"""派单算法统一调度"""
from typing import List, Tuple
from fault_recognize.predict import predict_fault
from order_dispatch.greedy import WeightedGreedyDispatch, WorkOrder, RepairWorker
from order_dispatch.pso import PSODispatch
from database.redis_oper import get_worker_real_time_status
from config.algorithm_config import DISPATCH_CONFIG

def smart_dispatch(fault_info, order_id, order_location, use_pso=False, batch_orders=None):
    """
    智能派单统一调度函数
    :param img_source: 故障图片路径/OSS URL
    :param order_id: 工单ID
    :param order_location: 工单位置（纬度，经度）
    :param use_pso: 是否使用PSO算法（批量派单）
    :param batch_orders: 批量工单列表（仅PSO使用）
    :return: 结构化派单结果
    """
    try:
        # 1. 判断故障信息是否合法
        if not fault_info["is_valid"]:
            return {
                "code": 400,
                "msg": "故障识别失败",
                "data": {"fault_info": fault_info}
            }

        # 2. 获取维修人员实时状态
        worker_list = get_worker_real_time_status()  # 从Redis读取
        if not worker_list:
            return {
                "code": 400,
                "msg": "无维修人员数据",
                "data": {"fault_info": fault_info}
            }

        # 3. 转换为RepairWorker对象
        workers = [
            RepairWorker(
                worker_id=w["worker_id"],
                name=w["name"],
                skills=w["skills"],
                location=(w["lat"], w["lng"]),
                load=w["load"],
                speed=w["speed"],
                is_available=w["is_available"]
            ) for w in worker_list
        ]

        # 4. 选择算法执行派单
        if use_pso and batch_orders:
            # PSO批量派单
            batch_work_orders = [
                WorkOrder(
                    order_id=o["order_id"],
                    fault_label=o["fault_label"],
                    location=(o["lat"], o["lng"])
                ) for o in batch_orders
            ]
            pso = PSODispatch(workers)
            dispatch_results = pso.dispatch_batch(batch_work_orders)
            # 转换结果格式
            results = [r.__dict__ for r in dispatch_results]
        else:
            # 贪心单工单派单
            order = WorkOrder(
                order_id=order_id,
                fault_label=fault_info["fault_label"],
                location=order_location
            )
            greedy = WeightedGreedyDispatch(workers)
            dispatch_result = greedy.dispatch(order)
            results = dispatch_result.__dict__

        # 5. 构造返回结果
        return {
            "code": 200,
            "msg": "派单成功",
            "data": {
                "fault_info": fault_info,
                "dispatch_result": results,
                "order_id": order_id,
                "order_location": order_location,
                "is_valid": results["comprehensive_score"] >= DISPATCH_CONFIG["comprehensive_score_threshold"],
            }
        }
    except Exception as e:
        print(f"智能派单失败: {e}")
        return {
            "code": 500,
            "msg": f"派单失败: {str(e)}",
            "data": {"fault_info": fault_info, "order_id": order_id}
        }