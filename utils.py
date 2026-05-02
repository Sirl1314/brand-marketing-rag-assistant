"""
工具模块 - 会话管理、文件操作等通用功能
"""

import os
import json
from datetime import datetime

# 常量定义
SESSIONS_DIR = "./sessions"
MAX_DISPLAY_SESSIONS = 5


def ensure_sessions_dir():
    """确保会话目录存在"""
    if not os.path.exists(SESSIONS_DIR):
        os.makedirs(SESSIONS_DIR)


def generate_session_id():
    """生成会话标识"""
    return datetime.now().strftime("%Y-%m-%d %H-%M-%S")


def get_session_file(session_id):
    """根据session_id获取文件路径"""
    return os.path.join(SESSIONS_DIR, f"{session_id}.json")


def load_sessions_list():
    """加载所有会话列表（按时间倒序）"""
    sessions = []
    if os.path.exists(SESSIONS_DIR):
        for filename in os.listdir(SESSIONS_DIR):
            if filename.endswith(".json"):
                sessions.append(filename[:-5])
    return sorted(sessions, reverse=True)


def create_new_session():
    """创建新会话"""
    ensure_sessions_dir()
    session_id = generate_session_id()
    session_data = {
        "current_session": session_id,
        "messages": [],
        "title": "新会话"  # 预留标题字段
    }
    with open(get_session_file(session_id), "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)
    return session_id


def load_session_data(session_id):
    """加载会话数据（带异常兜底）"""
    file_path = get_session_file(session_id)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 确保数据结构完整
                if "messages" not in data:
                    data["messages"] = []
                if "title" not in data:
                    data["title"] = "未命名会话"
                return data
        except (json.JSONDecodeError, Exception) as e:
            print(f"[警告] 会话文件损坏: {file_path}, 错误: {e}")
            # 自动重置为空会话
            return {"current_session": session_id, "messages": [], "title": "恢复的会话"}
    return {"current_session": session_id, "messages": [], "title": "新会话"}


def save_session_data(session_id, data):
    """保存会话数据"""
    try:
        with open(get_session_file(session_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[错误] 保存会话失败: {e}")
        return False


def delete_session(session_id):
    """删除会话"""
    file_path = get_session_file(session_id)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"[错误] 删除会话失败: {e}")
            return False
    return False


def update_session_title(session_id, first_message):
    """根据第一条消息自动生成会话标题"""
    if first_message and len(first_message) > 0:
        # 取前20个字符作为标题
        title = first_message[:20].strip()
        if len(first_message) > 20:
            title += "..."
        return title
    return "新会话"
