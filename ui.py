"""
界面模块 - Streamlit UI 组件与样式，打造传媒品牌营销质感
"""

import streamlit as st
from config import EXAMPLE_QUESTIONS

# ─── 品牌主题配色 ───────────────────────────────────────────────
THEME_CSS = """
<style>
/* 全局字体与背景 */
.stApp {
    background-color: #f5f6f8;
}

/* 顶部标题栏 */
.header-bar {
    background: linear-gradient(135deg, #1a2744 0%, #2c3e6b 100%);
    padding: 28px 36px 22px 36px;
    border-radius: 0 0 16px 16px;
    margin: -1rem -1rem 1.5rem -1rem;
    color: #ffffff;
}
.header-bar h1 {
    font-size: 1.65rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: 1px;
}
.header-bar p {
    font-size: 0.88rem;
    color: #b8c4e0;
    margin: 6px 0 0 0;
}

/* 侧边栏 */
section[data-testid="stSidebar"] {
    background-color: #1e2d4d;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li,
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #d0daf0;
}
section[data-testid="stSidebar"] .stMarkdown h2 {
    border-bottom: 2px solid #3a5280;
    padding-bottom: 6px;
}

/* 聊天气泡 */
.chat-user {
    background: linear-gradient(135deg, #2c3e6b, #3a5280);
    color: #ffffff;
    padding: 14px 20px;
    border-radius: 16px 16px 4px 16px;
    margin: 8px 0;
    font-size: 0.92rem;
    line-height: 1.65;
    max-width: 88%;
    margin-left: auto;
}
.chat-ai {
    background: #ffffff;
    color: #1a2744;
    padding: 14px 20px;
    border-radius: 16px 16px 16px 4px;
    margin: 8px 0;
    font-size: 0.92rem;
    line-height: 1.7;
    border-left: 4px solid #d4a853;
    max-width: 92%;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.chat-label {
    font-size: 0.75rem;
    font-weight: 600;
    margin-bottom: 2px;
    opacity: 0.7;
}

/* 示例问题按钮区域 */
.example-section {
    background: #ffffff;
    border: 1px solid #e2e6ee;
    border-radius: 12px;
    padding: 18px 22px;
    margin: 12px 0;
}

/* 知识库状态卡片 */
.kb-card {
    background: rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 14px 18px;
    margin: 10px 0;
    border: 1px solid rgba(255,255,255,0.1);
}
.kb-status-ok { color: #6ecf8e; font-weight: 600; }
.kb-status-warn { color: #f0c050; font-weight: 600; }

/* 隐藏 Streamlit 默认元素 */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* 输入框样式 */
.stTextInput > div > div > input {
    border-radius: 10px;
    border: 2px solid #d0d8e8;
    padding: 10px 14px;
}
.stTextInput > div > div > input:focus {
    border-color: #3a5280;
}

/* Chat input 样式优化 */
.stChatInput > div > div > textarea {
    border-radius: 10px;
    border: 2px solid #d0d8e8;
}
.stChatInput > div > div > textarea:focus {
    border-color: #3a5280;
}

/* 分隔线 */
hr {
    border: none;
    border-top: 1px solid #e2e6ee;
    margin: 1.2rem 0;
}
</style>
"""


def inject_theme():
    """注入品牌主题 CSS"""
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def render_header():
    """渲染品牌标题栏"""
    st.markdown("""
    <div class="header-bar">
        <h1>滩滩鱼传媒 · 品牌营销智能助手</h1>
        <p>基于 RAG 技术，融合公司案例库、方案库、文案库，为你提供专业营销支持</p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar(doc_count, kb_ready):
    """
    渲染侧边栏
    返回：(rebuild_clicked: bool, clear_clicked: bool)
    """
    with st.sidebar:
        st.markdown("## 项目介绍")
        st.markdown("""
        **滩滩鱼传媒营销AI助手**基于 RAG（检索增强生成）技术，
        将公司内部的营销案例、策划方案、活动 SOP 等知识
        结构化存入向量库，结合大语言模型为你生成专业回答。
        """)

        st.markdown("## 使用说明")
        st.markdown("""
        1. 在下方输入框提出你的营销问题
        2. AI 会从知识库检索相关内容
        3. 结合检索结果生成专业、可落地的回答
        """)

        st.markdown("---")
        st.markdown("## 知识库状态")

        # 状态卡片
        if kb_ready:
            st.markdown(f"""
            <div class="kb-card">
                <span class="kb-status-ok">● 已就绪</span><br>
                <span style="font-size:0.82rem;">文档数量：<b>{doc_count}</b> 篇</span><br>
                <span style="font-size:0.82rem;">向量库：已构建</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="kb-card">
                <span class="kb-status-warn">● 未构建</span><br>
                <span style="font-size:0.82rem;">请将文档放入 media_docs 目录后刷新</span>
            </div>
            """, unsafe_allow_html=True)

        rebuild = st.button("重建知识库", use_container_width=True)

        st.markdown("---")
        st.markdown("## 示例问题")
        for q in EXAMPLE_QUESTIONS:
            st.markdown(f"- {q}")

        st.markdown("---")
        clear = st.button("清空对话", use_container_width=True)

    return rebuild, clear


def render_example_buttons():
    """
    渲染可点击的示例问题按钮
    返回：被点击的问题文本，或 None
    """
    st.markdown('<div class="example-section">', unsafe_allow_html=True)
    st.markdown("**试试这些问题：**")

    clicked = None
    cols = st.columns(len(EXAMPLE_QUESTIONS))
    for i, q in enumerate(EXAMPLE_QUESTIONS):
        if cols[i].button(q, key=f"example_{i}", use_container_width=True):
            clicked = q

    st.markdown("</div>", unsafe_allow_html=True)
    return clicked


def render_chat_history():
    """渲染对话历史"""
    if "messages" not in st.session_state:
        return

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="chat-label" style="text-align:right;">你</div>
            <div class="chat-user">{msg["content"]}</div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-label">AI 助手</div>
            <div class="chat-ai">{msg["content"]}</div>
            """, unsafe_allow_html=True)


def render_user_input():
    """
    渲染用户输入区域
    返回：用户输入的文本，或空字符串
    """
    st.markdown("---")
    return st.chat_input(
        placeholder="输入你的营销问题，例如：给我一个茶饮品牌的年轻群体营销方案",
        key="user_input",
    )
