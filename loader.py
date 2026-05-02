"""
文档加载与分片模块 - 负责读取、解析和切分营销文档
"""

import os
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import DOCS_FOLDER, CHUNK_SIZE, CHUNK_OVERLAP, CHUNK_SEPARATORS


def load_docs(folder=DOCS_FOLDER):
    """
    扫描文档目录，加载所有 PDF 和 DOCX 文件
    返回：Document 对象列表
    """
    docs = []
    if not os.path.exists(folder):
        os.makedirs(folder)
        return docs

    files = [f for f in os.listdir(folder) if f.endswith((".pdf", ".docx"))]
    for filename in files:
        path = os.path.join(folder, filename)
        try:
            if filename.endswith(".pdf"):
                loader = PyPDFLoader(path)
            else:
                loader = Docx2txtLoader(path)
            docs.extend(loader.load())
        except Exception as e:
            print(f"[警告] 加载文件 {filename} 失败: {e}")
    return docs


def split_docs(docs):
    """
    按营销文档逻辑结构进行分片
    返回：分片后的 Document 对象列表
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=CHUNK_SEPARATORS,
    )
    return splitter.split_documents(docs)


def get_doc_count(folder=DOCS_FOLDER):
    """返回文档目录中的文档数量"""
    if not os.path.exists(folder):
        return 0
    return len([f for f in os.listdir(folder) if f.endswith((".pdf", ".docx"))])
