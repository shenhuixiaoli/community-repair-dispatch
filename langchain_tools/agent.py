from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from tools import LLM, tool_list
import time

# ===================== 【关键】使用 ReAct 模板（开源模型通用）=====================
react_template = """
你是专业的维修调度智能助手，你可以根据传入参数和场景智能选择工具执行。工具有：故障识别、智能派单、排期预测。

你必须使用工具获取真实数据，绝对不能编造！
你必须一步一步来，每一步只调用一个工具。


可用工具：
{tools}

【重要规则，必须严格遵守】
1. 多参数工具必须按 **JSON 对象格式** 传入所有必填参数
2. 格式必须严格如下，不可随意变化：

对于单参数工具（如fault_predict）：
Action: fault_predict
Action Input: "图片路径"

对于多参数工具（smart_dispatch、schedule_predict）：
Action: smart_dispatch
Action Input: {{"img_url":"图片路径", "order_id":"工单ID", "lat":纬度, "lng":经度}}


工具使用格式：
Question: 输入的问题
Thought: 思考步骤
Action: 工具名称，必须是 {tool_names} 中的一个
Action Input: 工具传入参数，不是json而是方法调用那样传递的参数
例如：
Action: fault_predict
Action Input: test3.jpg
Observation: 工具返回结果
Final Answer: 最终回答，必须包含：
1. 是否调用了工具
2. 调用了哪个工具
3. 传入参数是什么
4. 工具返回结果

开始！
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