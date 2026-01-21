import streamlit as st
import sqlite3
import pandas as pd
import PyPDF2
import google.generativeai as genai
import json

# --- 1. 页面设置 (必须在最前面) ---
st.set_page_config(page_title="BioBrain v2.5", layout="wide", page_icon="🧠")

# --- 2. 数据库与 AI 函数 ---
def get_connection():
    return sqlite3.connect("biobrain.db")

def init_db():
    conn = get_connection()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY, 
                title TEXT, 
                first_author TEXT, 
                year INTEGER, 
                category TEXT, 
                problem_solved TEXT, 
                key_finding TEXT, 
                methodology TEXT, 
                rating INTEGER
            )
        ''')
        conn.commit()
    except Exception as e:
        st.error(f"数据库初始化失败: {e}")
    finally:
        conn.close()

def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        # 读取前5页
        for page in pdf_reader.pages[:5]:
            text += page.extract_text()
        return text
    except Exception as e:
        return None

def analyze_with_gemini(api_key, text_content):
    try:
        genai.configure(api_key=api_key)
        # 使用您刚才确认可用的 2.5 Flash 模型
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        prompt = f"""
        You are an expert scientific researcher. Analyze the paper text.
        Return ONLY a JSON object. No Markdown.
        
        JSON Keys:
        - title
        - author
        - year (integer)
        - category (choose one: Gene Therapy, Cell Therapy, Targets, Clinical, AI, Methodology)
        - problem (summary of the bottleneck)
        - finding (summary of the solution)
        - method (key techniques)
        
        Text:
        {text_content[:30000]} 
        """
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        return {"error": str(e)}

# --- 3. 初始化 ---
init_db()

# --- 4. 侧边栏 (API Key) ---
with st.sidebar:
    st.header("⚙️ 设置")
    api_key = st.text_input("🔑 Gemini API Key", type="password")
    st.info("填入 Key 后按回车生效")
    st.markdown("---")
    menu = st.radio("导航", ["📥 录入文献 (Log Paper)", "📚 查看文献库 (Library)"])

# --- 5. 主界面逻辑 ---
st.title("🧠 BioBrain (Gemini 2.5版)")

if menu == "📥 录入文献 (Log Paper)":
    st.subheader("📄 上传 PDF")
    
    # 确保 session_state 存在
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {
            "title": "", "author": "", "year": 2026, "category": "Gene Therapy",
            "problem": "", "finding": "", "method": ""
        }

    # 上传组件
    uploaded_file = st.file_uploader("拖拽 PDF 到这里", type=["pdf"])

    # AI 分析按钮
    if uploaded_file:
        if st.button("✨ 用 AI 分析 (Analyze)"):
            if not api_key:
                st.error("❌ 请先在左侧侧边栏填入 API Key！")
            else:
                with st.spinner("🤖 Gemini 2.5 正在阅读
