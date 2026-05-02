"""
品牌营销智能助手（RAG）
主入口文件 - 采用现代聊天界面布局
"""

import os

# ⚠️ 必须在所有导入之前设置镜像！
# 尝试多个国内镜像源
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"  # 主镜像
# os.environ["HF_ENDPOINT"] = "https://modelscope.cn"  # 备用：ModelScope
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"  # 禁用遥测加速加载

import shutil
import logging
import streamlit as st
from config import DOCS_FOLDER, EXAMPLE_QUESTIONS, VECTOR_DB_PATH
from loader import load_docs, split_docs, get_doc_count
from rag_chain import load_vector_db, build_vector_db, get_qa_chain, close_vector_db
from utils import (
    SESSIONS_DIR, MAX_DISPLAY_SESSIONS,
    load_sessions_list, create_new_session,
    load_session_data, save_session_data, delete_session,
    update_session_title
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ── 页面配置 ─────────────────────────────────────────────────
st.set_page_config(
    page_title="品牌营销智能助手",
    page_icon="📢",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.logo("./logo.png")
# ─── 自定义主题样式 ───────────────────────────────────────────
st.markdown("""
<style>
/* 全局背景 */
.stApp {
    background-color: #0e1117;
}

/* 侧边栏样式 */
section[data-testid="stSidebar"] {
    background-color: #1a1d24;
}

section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #ffffff;
}

section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li {
    color: #b8bcc8;
}

/* 标题样式 */
.main-title {
    color: #ffffff;
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
}

.subtitle {
    color: #8b8fa3;
    font-size: 0.95rem;
    margin-bottom: 1.5rem;
}

/* 知识库状态卡片 */
.kb-status-card {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d4a6f 100%);
    border-radius: 12px;
    padding: 16px 20px;
    margin: 12px 0;
    border: 1px solid #3a5280;
}

.kb-status-ok {
    color: #4ade80;
    font-weight: 600;
}

/* 示例问题区域 */
.example-section {
    background: #1a1d24;
    border: 1px solid #2d3139;
    border-radius: 10px;
    padding: 14px 18px;
    margin: 10px 0;
}

/* 统计信息 */
.stats-text {
    font-size: 12px;
    color: #6b7280;
    margin-bottom: 10px;
}

/* 隐藏默认元素 */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def init_knowledge_base():
    """
    初始化知识库：若向量库已存在则直接加载，否则从文档构建
    返回：Chroma 向量库实例，失败返回 None
    """
    try:
        if not os.path.exists(VECTOR_DB_PATH):
            logger.info("首次启动，开始构建营销知识库...")
            with st.spinner("首次启动，正在构建营销知识库，请稍候..."):
                docs = load_docs()
                if not docs:
                    logger.warning("未找到任何文档")
                    return None
                texts = split_docs(docs)
                if not texts:
                    logger.warning("文档分片失败")
                    return None
                db = build_vector_db(texts)
                logger.info("知识库构建完成")
                st.success("✅ 知识库构建完成！")
                return db
        else:
            logger.info("加载已有向量库")
            return load_vector_db()
    except Exception as e:
        logger.error(f"知识库初始化失败: {e}", exc_info=True)
        return None


def process_question(question, qa_chain):
    """处理用户提问，返回 AI 回答字符串和模式信息"""
    try:
        result = qa_chain(question)
        answer = result.get("answer", "抱歉，未能获取有效回答")
        mode = result.get("mode", "unknown")
        context = result.get("context", "")
        
        if not isinstance(answer, str):
            answer = str(answer)
        
        return answer, mode, context
    except Exception as e:
        return f"抱歉，生成回答时出现错误：{e}", "error", ""


def init_kb_async():
    """异步初始化知识库（在后台线程中执行）"""
    try:
        db = init_knowledge_base()
        st.session_state.db = db
        st.session_state.kb_ready = db is not None
        if db is not None:
            st.session_state.qa_chain = get_qa_chain(db)
        return True
    except Exception as e:
        logger.error(f"知识库初始化失败: {e}")
        return False


def main():
    # ── 初始化会话状态（优先加载消息） ──────────────────────
    # 1. 先初始化会话（如果没有会话，创建一个）
    if "current_session" not in st.session_state:
        sessions = load_sessions_list()
        if sessions:
            st.session_state.current_session = sessions[0]
        else:
            st.session_state.current_session = create_new_session()
    
    # 2. 立即加载消息（优先显示历史对话）- 这是最快的操作
    if "messages_loaded" not in st.session_state or st.session_state.get("need_reload"):
        session_data = load_session_data(st.session_state.current_session)
        st.session_state.messages = session_data.get("messages", [])
        st.session_state.messages_loaded = True
        st.session_state.need_reload = False

    # 3. 初始化知识库状态（延迟加载）
    if "kb_ready" not in st.session_state:
        st.session_state.kb_ready = False
    if "db" not in st.session_state:
        st.session_state.db = None
    if "qa_chain" not in st.session_state:
        st.session_state.qa_chain = None
    if "kb_load_triggered" not in st.session_state:
        st.session_state.kb_load_triggered = False
    
    db = st.session_state.db
    kb_ready = st.session_state.kb_ready
    qa_chain = st.session_state.qa_chain
    
    # 4. 首次加载时触发知识库异步加载，但不阻塞页面渲染
    if not kb_ready and db is None and not st.session_state.kb_load_triggered:
        st.session_state.kb_load_triggered = True  # 标记已触发
        # 使用特殊标志触发 rerun 后再加载
        st.session_state["trigger_kb_load"] = True
        st.rerun()

    # ── 侧边栏 ──────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🎯 滩滩鱼传媒")

        doc_count = get_doc_count()

        # 知识库状态
        st.markdown("### 知识库状态")
        if not kb_ready and db is None:
            # 还未加载
            st.info("🔄 正在加载知识库...")
            st.markdown(f"""
            <div class="kb-status-card" style="background: linear-gradient(135deg, #3a3226 0%, #4a4236 100%); border-color: #6a5a3a;">
                <span style="color: #ffd700; font-weight: 600;">● 加载中...</span><br>
                <span style="font-size:0.85rem; color:#b8bcc8;">正在初始化向量库</span>
            </div>
            """, unsafe_allow_html=True)
        elif kb_ready:
            st.markdown(f"""
            <div class="kb-status-card">
                <span class="kb-status-ok">● 已就绪</span><br>
                <span style="font-size:0.85rem; color:#b8bcc8;">文档数量：<b>{doc_count}</b> 篇</span><br>
                <span style="font-size:0.85rem; color:#b8bcc8;">向量库：已构建</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("知识库未就绪，请将 PDF/DOCX 文件放入 media_docs 目录后重启。")

        st.divider()

        # 会话管理
        st.markdown("### 📝 会话管理")
        
        # 新建会话按钮
        if st.button("➕ 新建会话", use_container_width=True, type="secondary"):
            st.session_state.current_session = create_new_session()
            st.session_state.messages = []
            st.session_state.need_reload = True
            # 更新会话缓存
            st.session_state.sessions_cache = load_sessions_list()
            st.rerun()

        # 会话列表（缓存，避免重复加载）
        if "sessions_cache" not in st.session_state:
            st.session_state.sessions_cache = load_sessions_list()
        
        sessions = st.session_state.sessions_cache
        if sessions:
            st.markdown("#### 历史会话")
            for session_id in sessions[:MAX_DISPLAY_SESSIONS]:
                is_active = session_id == st.session_state.current_session
                
                # 使用两列布局：会话按钮 + 删除按钮
                col_session, col_delete = st.columns([0.82, 0.18])
                
                with col_session:
                    button_type = "primary" if is_active else "secondary"
                    if st.button(session_id, key=f"session_{session_id}", use_container_width=True, type=button_type):
                        st.session_state.current_session = session_id
                        st.session_state.need_reload = True
                        # 使用 JavaScript 滚动到页面顶部
                        st.markdown(
                            """
                            <script>
                                window.scrollTo({top: 0, behavior: 'smooth'});
                            </script>
                            """,
                            unsafe_allow_html=True
                        )
                        st.rerun()
                
                with col_delete:
                    # 只要有多个会话，就显示删除按钮
                    if len(sessions) > 1:
                        if st.button("❌", key=f"delete_{session_id}", use_container_width=True):
                            delete_session(session_id)
                            # 如果删除的是当前会话，切换到第一个会话
                            if session_id == st.session_state.current_session:
                                st.session_state.sessions_cache = load_sessions_list()
                                sessions = st.session_state.sessions_cache
                                if sessions:
                                    st.session_state.current_session = sessions[0]
                                    st.session_state.need_reload = True
                                else:
                                    st.session_state.current_session = create_new_session()
                                    st.session_state.messages = []
                            else:
                                # 刷新缓存
                                st.session_state.sessions_cache = load_sessions_list()
                            st.rerun()
                    else:
                        # 只有一个会话时，显示一个空占位符保持布局一致
                        st.markdown("&nbsp;", unsafe_allow_html=True)

        st.divider()

        # 重建知识库按钮
        if st.button("🔄 重建知识库", use_container_width=True, type="secondary"):
            try:
                # 1. 关闭旧数据库连接
                with st.spinner("正在释放数据库连接..."):
                    if "db" in st.session_state:
                        close_vector_db(st.session_state.db)
                        del st.session_state["db"]
                        logger.info("已释放向量库实例")

                    if "qa_chain" in st.session_state:
                        del st.session_state["qa_chain"]
                        logger.info("已释放问答链实例")

                    for key in ["kb_initialized", "kb_loading", "kb_ready", "kb_load_triggered"]:
                        if key in st.session_state:
                            del st.session_state[key]

                    import gc
                    gc.collect()
                    gc.collect()
                    import time
                    time.sleep(1)

                # 2. 删除向量库目录
                if os.path.exists(VECTOR_DB_PATH):
                    with st.spinner("正在删除旧知识库文件..."):
                        max_retries = 5
                        for retry in range(max_retries):
                            try:
                                import shutil
                                shutil.rmtree(VECTOR_DB_PATH)
                                logger.info(f"已删除向量库: {VECTOR_DB_PATH}")
                                break
                            except PermissionError as e:
                                if retry < max_retries - 1:
                                    logger.warning(f"删除失败，重试中 ({retry+1}/{max_retries})")
                                    gc.collect()
                                    time.sleep(1.5)
                                else:
                                    raise e

                # 3. 清空当前会话消息
                with st.spinner("正在重置会话..."):
                    st.session_state.messages = []
                    save_session_data(st.session_state.current_session, {
                        "current_session": st.session_state.current_session,
                        "messages": [],
                        "title": "新会话"
                    })

                st.success("✅ 知识库已清空，页面将重新构建...")
                st.rerun()
            except PermissionError as e:
                logger.error(f"文件被占用，无法删除: {e}")
                st.error("数据库文件正在使用中，请刷新页面后再试。")
            except Exception as e:
                logger.error(f"重建知识库失败: {e}", exc_info=True)
                st.error(f"重建失败: {e}")

        st.divider()

        # 使用说明
        st.markdown("### 使用说明")
        st.markdown("""
        1. 在下方输入框提出营销问题
        2. AI 会从知识库检索相关内容
        3. 结合检索结果生成专业回答
        """)

        st.divider()

        # 示例问题
        st.markdown("### 💡 示例问题")
        for i, q in enumerate(EXAMPLE_QUESTIONS):
            if st.button(q, key=f"example_{i}", use_container_width=True, type="secondary"):
                # 先保存到 session_state，再触发处理
                st.session_state["pending_question"] = q
                st.rerun()

        st.divider()

        # 清空对话按钮
        if st.button("❌ 清空对话", use_container_width=True, type="secondary"):
            st.session_state.messages = []
            save_session_data(st.session_state.current_session, {
                "current_session": st.session_state.current_session,
                "messages": [],
                "title": "新会话"
            })
            st.rerun()

    # ── 主聊天区域 ──────────────────────────────────────────

    # 标题
    st.markdown('<div class="main-title">滩滩鱼传媒 · 品牌营销智能助手</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">基于 RAG 技术，融合公司案例库、方案库、文案库，为你提供专业营销支持</div>', unsafe_allow_html=True)

    # 统计信息
    total = len(st.session_state.messages)
    user_count = sum(1 for m in st.session_state.messages if m["role"] == "user")
    ai_count = sum(1 for m in st.session_state.messages if m["role"] == "assistant")
    st.markdown(f"""
        <div class="stats-text">
            📊 总消息数: {total} | 我的消息: {user_count} | AI回复: {ai_count}
        </div>
    """, unsafe_allow_html=True)

    # 显示聊天历史
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 自动滚动到最新消息（改进版）
    st.markdown("""
    <script>
    // 滚动到底部
    function scrollToBottom() {
        // 找到聊天容器
        const chatContainer = document.querySelector('[data-testid="stVerticalBlock"]');
        if (chatContainer) {
            // 平滑滚动到底部
            chatContainer.scrollTo({
                top: chatContainer.scrollHeight,
                behavior: 'smooth'
            });
        }
    }
    
    // 页面加载完成后滚动
    setTimeout(scrollToBottom, 100);
    
    // 监听输入框事件，用户发送消息时滚动
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.addedNodes.length > 0) {
                // 延迟滚动，确保消息已渲染
                setTimeout(scrollToBottom, 200);
            }
        });
    });
    
    // 监听整个页面的变化
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    </script>
    """, unsafe_allow_html=True)

    # 处理待回答的问题（来自示例按钮）
    if "pending_question" in st.session_state:
        question = st.session_state.pop("pending_question")
        
        # 先保存用户消息
        st.session_state.messages.append({"role": "user", "content": question})
        
        # 如果是第一条消息，更新会话标题
        if len(st.session_state.messages) == 1:
            title = update_session_title(st.session_state.current_session, question)
            session_data = load_session_data(st.session_state.current_session)
            session_data["title"] = title
            save_session_data(st.session_state.current_session, session_data)
            # 刷新缓存
            st.session_state.sessions_cache = load_sessions_list()
        
        with st.chat_message("user"):
            st.markdown(question)

        if qa_chain:
            with st.chat_message("assistant"):
                # 先调用流式输出获取 mode
                result = qa_chain(question, stream=True)
                mode = result.get("mode", "unknown")
                
                # 根据模式显示标识
                if mode == "rag":
                    st.success("✅ 已从知识库检索相关内容")
                    answer_with_source = f"**📚 来源：知识库检索**\n\n"
                elif mode == "direct":
                    st.info("💡 知识库无相关内容，使用通用知识回答")
                    answer_with_source = f"**💡 来源：AI大模型通用知识**\n\n"
                else:
                    answer_with_source = ""
                
                # 流式输出
                if "stream" in result:
                    answer_placeholder = st.empty()
                    full_answer = ""
                    
                    for chunk in result["stream"]:
                        full_answer += chunk
                        answer_placeholder.markdown(answer_with_source + full_answer)
                    
                    st.session_state.messages.append({"role": "assistant", "content": answer_with_source + full_answer})
                else:
                    # 非流式模式（错误处理）
                    answer = result.get("answer", "")
                    st.markdown(answer_with_source + answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer_with_source + answer})
        else:
            # 知识库未就绪，直接使用大模型回答（流式）
            with st.chat_message("assistant"):
                try:
                    from rag_chain import _get_openai_client
                    from config import DIRECT_SYSTEM_PROMPT, LLM_TEMPERATURE, LLM_MAX_TOKENS
                    
                    client = _get_openai_client()
                    st.info("💡 知识库加载中，使用 AI 通用知识回答")
                    
                    answer_with_source = f"**💡 来源：AI大模型通用知识**\n\n"
                    answer_placeholder = st.empty()
                    full_answer = ""
                    
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": DIRECT_SYSTEM_PROMPT},
                            {"role": "user", "content": question}
                        ],
                        temperature=LLM_TEMPERATURE,
                        max_tokens=LLM_MAX_TOKENS,
                        stream=True,
                    )
                    
                    for chunk in response:
                        if chunk.choices and chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            full_answer += content
                            answer_placeholder.markdown(answer_with_source + full_answer)
                    
                    st.session_state.messages.append({"role": "assistant", "content": answer_with_source + full_answer})
                except Exception as e:
                    st.error(f"抱歉，生成回答时出现错误：{e}")
                    answer_with_source = f"抱歉，生成回答时出现错误：{e}"
                    st.session_state.messages.append({"role": "assistant", "content": answer_with_source})

        # 保存会话数据到JSON文件
        save_session_data(st.session_state.current_session, {
            "current_session": st.session_state.current_session,
            "messages": st.session_state.messages
        })
        st.rerun()

    # 聊天输入框
    prompt = st.chat_input("输入你的营销问题，例如：给我一个茶饮品牌的年轻群体营销方案")
    if prompt:
        # 先保存用户消息到 session_state
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 调用 AI 回答（知识库未就绪时使用直连模式）
        with st.chat_message("assistant"):
            if qa_chain:
                # 知识库已就绪，使用 RAG 链（流式）
                result = qa_chain(prompt, stream=True)
                mode = result.get("mode", "unknown")
                
                # 显示回答和模式标识
                if mode == "rag":
                    st.success("✅ 已从知识库检索相关内容")
                    answer_with_source = f"**📚 来源：知识库检索**\n\n"
                elif mode == "direct":
                    st.info("💡 知识库无相关内容，使用通用知识回答")
                    answer_with_source = f"**💡 来源：AI大模型通用知识**\n\n"
                else:
                    answer_with_source = ""
                
                # 流式输出
                if "stream" in result:
                    answer_placeholder = st.empty()
                    full_answer = ""
                    
                    for chunk in result["stream"]:
                        full_answer += chunk
                        answer_placeholder.markdown(answer_with_source + full_answer)
                    
                    st.session_state.messages.append({"role": "assistant", "content": answer_with_source + full_answer})
                else:
                    # 非流式模式（错误处理）
                    answer = result.get("answer", "")
                    st.markdown(answer_with_source + answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer_with_source + answer})
            else:
                # 知识库未就绪，直接使用大模型回答（流式）
                try:
                    from rag_chain import _get_openai_client
                    from config import DIRECT_SYSTEM_PROMPT, LLM_TEMPERATURE, LLM_MAX_TOKENS
                    
                    client = _get_openai_client()
                    st.info("💡 知识库加载中，使用 AI 通用知识回答")
                    
                    answer_with_source = f"** 来源：AI大模型通用知识**\n\n"
                    answer_placeholder = st.empty()
                    full_answer = ""
                    
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": DIRECT_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=LLM_TEMPERATURE,
                        max_tokens=LLM_MAX_TOKENS,
                        stream=True,
                    )
                    
                    for chunk in response:
                        if chunk.choices and chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            full_answer += content
                            answer_placeholder.markdown(answer_with_source + full_answer)
                    
                    st.session_state.messages.append({"role": "assistant", "content": answer_with_source + full_answer})
                except Exception as e:
                    st.error(f"抱歉，生成回答时出现错误：{e}")
                    answer_with_source = f"抱歉，生成回答时出现错误：{e}"
                    st.session_state.messages.append({"role": "assistant", "content": answer_with_source})

        # 保存 AI 回答到 session_state（已在流式输出时保存，这里不需要重复保存）
        # 保存会话数据到JSON文件
        save_session_data(st.session_state.current_session, {
            "current_session": st.session_state.current_session,
            "messages": st.session_state.messages
        })
        st.rerun()

    # ── 页面底部：异步加载知识库（在页面渲染完成后执行） ──────────
    # 使用 trigger_kb_load 标志确保在页面完全渲染后再加载
    if st.session_state.get("trigger_kb_load") and not kb_ready and db is None:
        # 清除触发标志
        del st.session_state["trigger_kb_load"]
        
        # 在页面底部显示加载提示（不阻塞页面）
        with st.sidebar:
            with st.spinner("正在加载知识库..."):
                # 后台加载知识库
                db = init_knowledge_base()
                st.session_state.db = db
                st.session_state.kb_ready = db is not None
                if db is not None:
                    st.session_state.qa_chain = get_qa_chain(db)
        
        # 加载完成后刷新页面，更新状态显示
        if db is not None:
            st.rerun()


if __name__ == "__main__":
    main()











