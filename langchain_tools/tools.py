from langchain_core.tools import Tool
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import requests
import json

# ************************** 配置项 **************************
ALGORITHM_API = {
    "fault_predict": "http://127.0.0.1:5000/api/fault/predict",
    "smart_dispatch": "http://127.0.0.1:5000/api/dispatch/smart",
    "schedule_predict": "http://127.0.0.1:5000/api/schedule/predict"
}

LLM = ChatOpenAI(
    base_url='https://api-inference.modelscope.cn/v1',
    model="deepseek-ai/DeepSeek-R1-0528",
    api_key="ms-f51cd024-834e-4b21-ad1d-36918f0ce83f",
    temperature=0,
    max_retries=1
)


# ************************** 1. 故障识别（单一JSON参数） **************************
def fault_predict_tool(params: str):
    try:
        data = json.loads(params)
        img_url = data["img_url"]

        headers = {"Content-Type": "application/json"}
        response = requests.post(
            ALGORITHM_API["fault_predict"],
            headers=headers,
            json={"img_url": img_url}
        )
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
作用：故障图片AI识别，返回类型、等级、置信度
【参数格式：单个JSON字符串】
{"img_url":"图片路径"}
使用场景：工单创建后、派单前必须调用
""",
    args_schema=None
)


# ************************** 2. 智能派单（单一JSON参数） **************************
def smart_dispatch_tool(params: str):
    try:
        data = json.loads(params)

        payload = {
            "fault_info": data.get("fault_info"),
            "order_id": data.get("order_id"),
            "lat": data.get("lat"),
            "lng": data.get("lng"),
            "use_pso": data.get("use_pso", False),
            "batch_orders": data.get("batch_orders")
        }

        headers = {"Content-Type": "application/json"}
        response = requests.post(
            ALGORITHM_API["smart_dispatch"],
            headers=headers,
            json=payload
        )
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
作用：基于多目标优化分配维修人员
【参数格式：单个JSON字符串】
{"fault_info":{},"order_id":"","lat":31.23,"lng":121.47,"use_pso":false}
使用场景：故障识别完成后调用
""",
    args_schema=None
)


# ************************** 3. 排期预测（已统一为单一JSON参数） **************************
def schedule_predict_tool(params: str):
    try:
        data = json.loads(params)

        payload = {
            "order_id": data.get("order_id"),
            "dispatch_result": data.get("dispatch_result"),
            "lat": data.get("lat"),
            "lng": data.get("lng")
        }

        headers = {"Content-Type": "application/json"}
        response = requests.post(
            ALGORITHM_API["schedule_predict"],
            headers=headers,
            json=payload
        )
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
作用：预测维修时长、缓冲时间、截止时间
【参数格式：单个JSON字符串】
{"order_id":"","dispatch_result":{},"lat":31.23,"lng":121.47}
使用场景：派单完成后才能调用
""",
    args_schema=None
)

# ************************** 最终工具集 **************************
tool_list = [fault_tool, dispatch_tool, schedule_tool]

print("✅ 三个算法工具封装完成！")
print(f"可用工具：{[tool.name for tool in tool_list]}")