"""
RAG 链模块 - 向量库构建、检索和问答链
"""
import os
import logging

# 设置 HuggingFace 国内镜像，加速模型下载
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

import shutil
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from openai import OpenAI
from config import (
    OPENAI_API_KEY, VECTOR_DB_PATH,
    RETRIEVAL_TOP_K, LLM_TEMPERATURE, LLM_MAX_TOKENS,
    SYSTEM_PROMPT, USER_PROMPT, DIRECT_SYSTEM_PROMPT
)

# 全局缓存
_embeddings_cache = None
_client = None  # LLM 客户端全局单例


def _get_openai_client():
    """获取全局唯一的 OpenAI 客户端（单例模式）"""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=OPENAI_API_KEY,  # 统一用 config 里的密钥
            base_url="https://api.deepseek.com/v1"  # 必须带 /v1
        )
    return _client


def _get_embeddings():
    """获取 Embedding 实例（使用本地模型）"""
    global _embeddings_cache
    if _embeddings_cache is not None:
        return _embeddings_cache

    # 使用已下载的本地模型
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        # 使用本地模型路径（已手动下载）
        local_model_path = "./models/bge-small-zh-v1.5"
        _embeddings_cache = HuggingFaceEmbeddings(
            model_name=local_model_path,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        return _embeddings_cache

    except Exception as e:
        raise RuntimeError(
            f"本地模型加载失败: {e}\n请执行: python -c \"import os; os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'; from huggingface_hub import snapshot_download; snapshot_download(repo_id='BAAI/bge-small-zh-v1.5', local_dir='./models/bge-small-zh-v1.5')\""
        )


def build_vector_db(texts):
    emb = _get_embeddings()
    db = Chroma.from_documents(texts, emb, persist_directory=VECTOR_DB_PATH)
    return db


def load_vector_db():
    emb = _get_embeddings()
    return Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=emb)


def close_vector_db(db):
    """显式关闭向量数据库连接，释放文件句柄

    注意：不能调用 _system.stop()，chromadb 的 Rust 后端是模块级单例，
    stop 后无法重启，会导致后续 PersistentClient 创建时 tenant 报错。
    """
    global _embeddings_cache
    try:
        # 1. 关闭底层 chromadb 客户端的 SQLite 连接
        if hasattr(db, '_client'):
            client = db._client
            if hasattr(client, '_db'):
                try:
                    client._db.close()
                except Exception:
                    pass
            if hasattr(client, '_connection'):
                try:
                    client._connection.close()
                except Exception:
                    pass
            if hasattr(client, 'close'):
                try:
                    client.close()
                except Exception:
                    pass

        # 2. 删除所有内部引用，帮助 GC 回收文件句柄
        for attr in ('_client', '_collection', '_index'):
            if hasattr(db, attr):
                try:
                    delattr(db, attr)
                except Exception:
                    pass

        # 3. 清除 chromadb 的单例缓存，避免删除目录后重建时 tenant 报错
        try:
            from chromadb.api.client import SharedSystemClient
            SharedSystemClient.clear_system_cache()
        except Exception:
            pass

        # 4. 重置全局 embedding 缓存，释放模型引用
        _embeddings_cache = None

        logger.info("向量数据库连接已关闭")
    except Exception as e:
        logger.warning(f"关闭向量数据库时出现警告: {e}")


def rebuild_vector_db(texts):
    if os.path.exists(VECTOR_DB_PATH):
        shutil.rmtree(VECTOR_DB_PATH)
    return build_vector_db(texts)


def get_qa_chain(db):
    """
    构建 RAG 问答链（智能路由）
    返回：question -> {"answer":..., "context":..., "mode":...}
    """
    client = _get_openai_client()
    retriever = db.as_retriever(search_kwargs={"k": RETRIEVAL_TOP_K})

    def rag_chain(question, stream=False):
        try:
            print("\n" + "="*60)
            print(f"🔍 用户问题: {question}")
            print("="*60)

            # 1. 检索相关文档
            docs = retriever.invoke(question)
            
            # 获取带分数的文档内容
            context_parts = []
            total_score = 0
            doc_count = 0
            
            for doc in docs:
                if doc.page_content and doc.page_content.strip():
                    context_parts.append(doc.page_content)
                    # 获取检索分数（如果有的话）
                    if hasattr(doc, 'metadata') and 'score' in doc.metadata:
                        total_score += doc.metadata['score']
                        doc_count += 1
            
            context = "\n\n".join(context_parts)
            
            # 计算平均分数（如果有分数信息）
            avg_score = total_score / doc_count if doc_count > 0 else None
            
            # 2. 智能路由：判断检索内容是否真的相关
            # 综合策略：检查检索分数 + 关键词匹配
            is_rag_mode = False
            
            if context.strip():
                # 提取问题中的关键词（中文字符）
                import re
                question_keywords = re.findall(r'[\u4e00-\u9fa5]{2,}', question)
                
                # 检查关键词是否出现在上下文中
                keyword_match_count = sum(1 for kw in question_keywords if kw in context)
                match_ratio = keyword_match_count / len(question_keywords) if question_keywords else 0
                
                # 更宽松的判断逻辑：
                # 1. 如果有分数信息且分数很低（<0.2），认为不相关
                # 2. 如果关键词匹配度低于10%，认为不相关
                # 3. 如果问题关键词少于1个，使用直连模式
                # 4. 默认使用RAG模式（优先使用知识库）
                should_use_rag = True
                
                # 检查分数（如果可用）- 降低阈值
                if avg_score is not None and avg_score < 0.2:
                    should_use_rag = False
                    reason = f"检索分数过低 ({avg_score:.2f})"
                # 检查关键词匹配 - 降低阈值
                elif match_ratio < 0.1:
                    should_use_rag = False
                    reason = f"关键词匹配度低 ({match_ratio:.1%})"
                # 检查关键词数量 - 降低要求
                elif len(question_keywords) < 1:
                    should_use_rag = False
                    reason = f"关键词数量不足 ({len(question_keywords)})"
                
                if should_use_rag:
                    # 安全格式化分数
                    score_str = f"{avg_score:.2f}" if avg_score is not None else "N/A"
                    print(f"📚 RAG 模式 - 检索到相关内容 (匹配度: {match_ratio:.1%}, 分数: {score_str})")
                    # 安全格式化，确保 context 不为 None
                    safe_context = context if context is not None else ""
                    system_content = SYSTEM_PROMPT.format(context=safe_context)
                    mode = "rag"
                    is_rag_mode = True
                else:
                    print(f"💡 直连模式 - {reason}")
                    system_content = DIRECT_SYSTEM_PROMPT
                    mode = "direct"
                    context = ""
            else:
                print(f"💡 直连模式 - 知识库无匹配内容")
                system_content = DIRECT_SYSTEM_PROMPT
                mode = "direct"
                context = ""

            # 3. LLM 调用（支持流式输出）
            if stream:
                # 流式输出模式
                def stream_generator():
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": system_content},
                            {"role": "user", "content": question}
                        ],
                        temperature=LLM_TEMPERATURE,
                        max_tokens=LLM_MAX_TOKENS,
                        stream=True,  # 启用流式
                    )
                    
                    full_answer = ""
                    for chunk in response:
                        if chunk.choices and chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            full_answer += content
                            yield content
                    
                    print(f"\n✅ AI 回答（流式完成）：")
                    print("-"*60)
                    print(full_answer)
                    print("-"*60)
                    print("="*60 + "\n")
                
                return {
                    "stream": stream_generator(),
                    "context": context if mode == "rag" else "",
                    "mode": mode
                }
            else:
                # 非流式模式（保持兼容）
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": question}
                    ],
                    temperature=LLM_TEMPERATURE,
                    max_tokens=LLM_MAX_TOKENS,
                )

                answer = response.choices[0].message.content.strip()

                print(f"\n✅ AI 回答：")
                print("-"*60)
                print(answer)
                print("-"*60)
                print("="*60 + "\n")

                return {
                    "answer": answer,
                    "context": context if mode == "rag" else "",
                    "mode": mode
                }

        except Exception as e:
            error_msg = f"服务异常，请稍后重试（错误：{str(e)}）"
            print(f"❌ 错误：{e}")
            return {
                "answer": error_msg,
                "context": "",
                "mode": "error"
            }

    return rag_chain