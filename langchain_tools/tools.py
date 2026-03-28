from langchain_core.tools import Tool
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import requests
import json

# ************************** 配置项 **************************
# 1. 算法API地址（你已集成的Flask算法服务地址）
ALGORITHM_API = {
    "fault_predict": "http://127.0.0.1:5000/api/fault/predict",
    "smart_dispatch": "http://127.0.0.1:5000/api/dispatch/smart",
    "schedule_predict": "http://127.0.0.1:5000/api/schedule/predict"
}

# 2. LLM配置（课题中可使用开源LLM如Qwen/GLM，或闭源如GPT-3.5/4）
LLM = ChatOpenAI(
    base_url='https://api-inference.modelscope.cn/v1',
    model="deepseek-ai/DeepSeek-R1-0528",
    api_key="ms-f51cd024-834e-4b21-ad1d-36918f0ce83f",
    temperature=0, # 决策场景设为0，保证结果确定性
    max_retries=1
)

# ************************** 1. 故障识别算法工具 **************************
def fault_predict_tool(img_url: str):
    """
    故障识别算法工具：调用故障识别API，返回故障类型、置信度等结果
    :param img_url: 故障图片路径/OSS URL
    :return: 故障识别结构化结果
    """
    try:
        headers = {"Content-Type": "application/json"}
        data = {"img_url": img_url}
        response = requests.post(ALGORITHM_API["fault_predict"], headers=headers, json=data)
        return response.json()
    except Exception as e:
        return {
            "code": 500,
            "msg": f"故障识别工具调用失败：{str(e)}",
            "data": None
        }

fault_tool = Tool(
    name="fault_predict",
    func=fault_predict_tool,
    description="""
工具名称：fault_predict
工具作用：对故障图片进行AI识别，返回故障类型、故障等级、置信度
入参要求：
  - img_url：字符串，必选，故障图片的OSS URL或本地路径
出参格式：{"code":200/400/500,"msg":"结果描述","data":{故障详细信息}}
使用场景：工单创建后、派单前必须调用，用于获取故障基础信息
    """,
    args_schema=None
)

# ************************** 2. 智能派单算法工具 **************************
def smart_dispatch_tool(img_url: str, order_id: str, lat: float, lng: float, use_pso: bool = False, batch_orders=None):
    """
    智能派单算法工具：多目标优化派单，返回最优维修人员、距离、耗时等
    :param img_url: 故障图片URL
    :param order_id: 工单ID
    :param lat: 纬度
    :param lng: 经度
    :param use_pso: 是否使用粒子群优化
    :param batch_orders: 批量工单（可选）
    :return: 派单结果
    """
    try:
        headers = {"Content-Type": "application/json"}
        data = {
            "img_url": img_url,
            "order_id": order_id,
            "lat": lat,
            "lng": lng,
            "use_pso": use_pso,
            "batch_orders": batch_orders
        }
        response = requests.post(ALGORITHM_API["smart_dispatch"], headers=headers, json=data)
        return response.json()
    except Exception as e:
        return {
            "code": 500,
            "msg": f"智能派单工具调用失败：{str(e)}",
            "data": None
        }

dispatch_tool = Tool(
    name="smart_dispatch",
    func=smart_dispatch_tool,
    description="""
工具名称：smart_dispatch
工具作用：基于多目标优化算法，为维修工单智能分配最优维修人员
入参要求：
  - img_url：字符串，必选，故障图片URL
  - order_id：字符串，必选，工单唯一标识
  - lat：浮点数，必选，工单纬度
  - lng：浮点数，必选，工单经度
  - use_pso：布尔值，可选，是否开启PSO优化（默认False）
  - batch_orders：可选，批量工单数据
出参格式：{"code":200/400/500,"msg":"描述","data":{"technician":{}, "distance":{}, "time":{}}}
使用场景：故障识别完成后，为工单分配维修人员时调用
    """,
    args_schema=None
)

# ************************** 3. 排期预测算法工具（你原有代码已完善） **************************
def schedule_predict_tool(order_id: str, img_source: str, lat: float, lng: float):
    """
    排期预测算法工具的核心执行逻辑：调用排期算法API，返回结构化结果
    :param order_id: 工单ID
    :param img_source: 故障图片路径/OSS URL
    :param lat: 工单位置纬度
    :param lng: 工单位置经度
    :return: 算法API返回的结构化结果
    """
    try:
        headers = {"Content-Type": "application/json"}
        data = {
            "img_url": img_source,
            "order_id": order_id,
            "lat": lat,
            "lng": lng
        }
        response = requests.post(ALGORITHM_API["schedule_predict"], headers=headers, json=data)
        return response.json()
    except Exception as e:
        return {
            "code": 500,
            "msg": f"排期算法工具调用失败：{str(e)}",
            "data": None
        }

schedule_tool = Tool(
    name="schedule_predict",
    func=schedule_predict_tool,
    description="""
工具名称：schedule_predict
工具作用：调用维修排期预测算法（随机森林模型），为已派单的工单预测维修时长、缓冲时间和截止时间
入参要求：
  - order_id：字符串，必选，工单唯一标识（如SCHEDULE20260323001）
  - img_source：字符串，必选，故障图片的OSS URL/本地路径
  - lat：浮点数，必选，工单位置的纬度（如31.2305）
  - lng：浮点数，必选，工单位置的经度（如121.4738）
出参格式：{"code":200/400/500,"msg":"执行结果描述","data":{"fault_info":{}, "dispatch_result":{}, "schedule_result":{}}}
使用场景：仅当工单已完成派单，且维修人员匹配成功时调用，禁止在派单失败时调用
    """,
    args_schema=None
)

# ************************** 最终工具集（可直接给大模型使用） **************************
tool_list = [fault_tool, dispatch_tool, schedule_tool]

# 输出工具列表，验证封装成功
print("✅ 三个算法工具封装完成！")
print(f"可用工具：{[tool.name for tool in tool_list]}")