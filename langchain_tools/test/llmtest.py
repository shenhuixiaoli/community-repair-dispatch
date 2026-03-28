from langchain_openai import ChatOpenAI


# 你的配置
LLM = ChatOpenAI(
    base_url='https://api-inference.modelscope.cn/v1',
    model="deepseek-ai/DeepSeek-R1-0528",
    api_key="ms-f51cd024-834e-4b21-ad1d-36918f0ce83f",
    temperature=0, # 决策场景设为0，保证结果确定性
    max_retries=1
)

# 测试：只发一个简单问题，不调用任何工具
if __name__ == '__main__':
    try:
        response = LLM.invoke("你好，请简单介绍一下你自己")
        print("✅ LLM 配置可用！返回内容：")
        print(response.content)
    except Exception as e:
        print("❌ LLM 调用失败：")
        print(e)
