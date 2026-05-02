"""
配置模块 - 管理环境变量、路径和全局参数
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# API 配置
OPENAI_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("请在 .env 文件中设置 DEEPSEEK_API_KEY")

# 路径配置
DOCS_FOLDER = "./media_docs"
VECTOR_DB_PATH = "./jc_vector_db"

# RAG 参数（更细的分片）
CHUNK_SIZE = 300  # 减小分片大小，让分片更细
CHUNK_OVERLAP = 50  # 减小重叠部分
RETRIEVAL_TOP_K = 6  # 增加检索数量，补偿更细的分片
LLM_TEMPERATURE = 0.2
LLM_MAX_TOKENS = 1024

# 分片分隔符（针对营销文档结构）
CHUNK_SEPARATORS = [
    "\n\n", "##", "###",
    "创意策略", "执行方案", "活动SOP",
    "\n", " "
]

# LLM 系统提示词
SYSTEM_PROMPT = """你是一位专业的品牌营销顾问，隶属于滩滩鱼传媒。请基于以下公司知识库内容回答问题。

要求：
1. 优先使用上下文中的信息来回答，确保内容准确
2. 回答要专业、有条理，适合传媒行业从业者阅读
3. 如果涉及方案或策略，请给出结构化、可执行的建议
4. 如果上下文中确实没有相关信息，请如实说明，不要编造

上下文信息：
{context}"""

USER_PROMPT = "{input}"

# 直连模式的系统提示词（不依赖知识库）
DIRECT_SYSTEM_PROMPT = """你是一位专业的品牌营销顾问，隶属于滩滩鱼传媒。
请基于你的专业知识回答问题，要求：
1. 回答要专业、有条理，适合传媒行业从业者阅读
2. 如果涉及方案或策略，请给出结构化、可执行的建议
3. 如果问题超出你的知识范围，请如实说明"""

# 示例问题列表
EXAMPLE_QUESTIONS = [
    "给我一个茶饮品牌的年轻群体营销方案",
    "写一条短视频带货文案",
    "线下活动执行SOP是什么？",
    "推荐3个品牌传播成功案例思路",
]
