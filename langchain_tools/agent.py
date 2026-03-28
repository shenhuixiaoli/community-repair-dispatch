from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from tools import LLM
from tools import tool_list

# ===================== 优化版提示词（强制输出工具信息）=====================
prompt = ChatPromptTemplate.from_messages([
    ("system", """
你是专业的维修调度智能助手，必须严格遵守以下规则：

1. 执行流程：故障识别 → 智能派单 → 排期预测
2. 必须调用工具获取真实数据，**绝对禁止编造结果**
3. 回答时**必须明确说明**：
   - 是否调用了工具
   - 调用的工具名称
   - 传入的参数是什么
   - 工具返回的结果

回答格式要求清晰易懂，让用户能明确看到工具调用全过程。
"""),
    ("user", "{input}"),
    ("system", "{agent_scratchpad}")
])

# 创建支持工具调用的 Agent
agent = create_openai_tools_agent(LLM, tool_list, prompt)

# 执行器
agent_executor = AgentExecutor(
    agent=agent,
    tools=tool_list,
    verbose=True,
    handle_parsing_errors=True
)

# ===================== 核心封装方法：控制台交互 =====================
def chat_repair_dispatcher():
    """
    维修调度智能助手 - 控制台交互方法
    输入问题 → 智能调用工具 → 输出答案（含工具调用详情）
    """
    print("=" * 60)
    print("🤖 维修调度智能助手已启动")
    print("输入 'quit' 或 'exit' 退出")
    print("=" * 60)

    while True:
        user_input = input("\n🗣️ 请输入你的问题：")

        # 退出逻辑
        if user_input.lower() in ["quit", "exit", "q"]:
            print("👋 再见！")
            break

        if not user_input.strip():
            print("⚠️ 请输入有效问题！")
            continue

        try:
            # 执行智能体
            result = agent_executor.invoke({"input": user_input})
            print("\n" + "=" * 60)
            print("🤖 助手回答：")
            print(result["output"])
            print("=" * 60)

        except Exception as e:
            print(f"\n❌ 执行出错：{str(e)}")

# ===================== 启动程序 =====================
if __name__ == '__main__':
    chat_repair_dispatcher()