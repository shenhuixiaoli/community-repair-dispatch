from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from tools import LLM, tool_list
import time
import threading


# ===================== 【核心】超时控制工具包装器 =====================
def tool_with_timeout(tool_func, timeout=30):
    """
    工具调用超时包装器：10秒内未返回则触发失败
    :param tool_func: 原工具函数
    :param timeout: 超时时间（默认10秒）
    :return: 包装后的工具函数
    """

    def wrapper(params: str):
        result = {"code": 504, "msg": "工具调用超时", "data": None}

        def target():
            nonlocal result
            try:
                # 执行原工具函数
                res = tool_func(params)
                result = res
            except Exception as e:
                result = {"code": 500, "msg": f"工具调用异常：{str(e)}", "data": None}

        # 启动线程执行工具调用
        t = threading.Thread(target=target)
        t.start()
        # 等待线程结束，超时则终止
        t.join(timeout=timeout)

        # 超时判断：线程仍在运行 → 超时失败
        if t.is_alive():
            return {
                "code": 504,
                "msg": "工具调用超时（10秒内未返回结果）",
                "data": {
                    "failure_scene": "工具执行超时",
                    "timeout_seconds": 10,
                    "suggestion": "请检查算法API是否正常运行、网络是否通畅，或稍后重试"
                }
            }
        return result

    return wrapper

# ===================== 【关键】更新工具列表（添加超时控制） =====================
# 为所有工具添加10秒超时包装
tool_list_with_timeout = [
    Tool(
        name=tool.name,
        func=tool_with_timeout(tool.func),  # 包装超时控制
        description=tool.description,
        args_schema=tool.args_schema
    ) for tool in tool_list
]

# ===================== 【关键】使用 ReAct 模板（开源模型通用）=====================
react_template = """
你是智能社区系统的算法工具调用智能体，核心职责是根据业务场景和传入参数，智能决策算法工具的调用顺序和参数，仅调用agent_tool_list中的工具，不做任何工程化操作。

【核心规则】
1. 工具调用必须基于业务场景，按「业务逻辑顺序」调用，前一个工具返回is_valid=true后，才能调用下一个工具；
2. 所有工具均接收「单个JSON字符串参数」，必须严格按工具注释的入参要求封装，参数缺失时直接返回调用失败，不编造参数；
3. 仅返回结构化结果，包含is_success、error_msg、decision_desc、tool_call_order、algorithm_results，格式固定，不添加额外内容；
4. 若某一步工具调用失败（is_valid=false），立即停止后续工具调用，返回已调用结果和失败原因；
5. 可用业务场景：
   - 物业报修全流程：按fault_predict→smart_dispatch→schedule_predict顺序调用；
   - 单独故障识别：仅调用fault_predict；
   - 单独智能派单：故障识别完成后，仅调用smart_dispatch；
   - 单独维修排期：派单完成后，仅调用schedule_predict。
6. 工具调用结果分两种情况，按对应模板处理：
   - 成功（code=200）：立即输出Final Answer（自然语言总结），停止所有操作。
   - 失败（code≠200）：立即输出调用失败，并且尝试分析为什么失败。
7. 工具调用超时属于失败场景。此时输出什么工具调用超时即可。

【可用工具】
{tools}
【工具名称列表】
{tool_names}

【执行格式】
Thought: 基于当前业务场景和参数，思考需要调用哪个/哪些工具，按什么顺序调用
Action: 工具名称（必须在{tool_names}中）
Action Input: 单个JSON字符串参数（严格按工具入参要求封装）
Observation: 工具返回的结构化结果
Final Answer: 按固定格式返回结构化算法结果，仅包含is_success、error_msg、decision_desc、tool_call_order、algorithm_results

开始执行！
Question: {input}
Thought: {agent_scratchpad}
"""

# 创建提示词
prompt = PromptTemplate.from_template(react_template)

# ===================== 【核心】创建 ReAct 智能体（所有开源模型都能用！）=====================
agent = create_react_agent(llm=LLM, tools=tool_list, prompt=prompt)

# 执行器
agent_executor = AgentExecutor(
    agent=agent,
    tools=tool_list,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=5,
    max_retry=2
)

# ===================== 控制台交互方法 =====================
def chat_repair_dispatcher():
    print("=" * 60)
    print("🤖 维修调度智能助手（ReAct模式）")
    print("输入 'quit' 退出")
    print("=" * 60)

    while True:
        user_input = input("\n🗣️ 请输入问题：")
        if user_input.lower() in ["quit", "exit"]:
            print("👋 再见")
            break

        try:
            #打印llm前置日志
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] llm接收请求 {user_input} ")

            result = agent_executor.invoke({
                "input": user_input,
                "tools": tool_list,
                "tool_names": [tool.name for tool in tool_list]
            })

            #打印llm后置日志
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] llm响应请求 {result}")
        except Exception as e:
            print("\n❌ 执行异常：", e)

if __name__ == '__main__':
    chat_repair_dispatcher()