import streamlit as st
import sqlite3
import pandas as pd
import PyPDF2
import google.generativeai as genai
import json

# --- 1. Database & Config ---
def get_connection():
    return sqlite3.connect("biobrain.db")

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # 确保表结构完整
    c.execute('''
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
    conn.close()

# --- 2. Real AI Analysis (Powered by Gemini 2.5) ---
def analyze_with_gemini(api_key, text_content):
    try:
        genai.configure(api_key=api_key)
        # 🎯 核心修改：使用您列表里确认可用的 2.5 Flash 模型
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        prompt = f"""
        You are an expert scientific researcher. Analyze the following academic paper text.
        Extract key insights and return ONLY a valid JSON object. Do not use Markdown formatting.
        
        JSON Keys:
        - title: Full paper title.
        - author: First author's last name (e.g., 'Wang et al.').
        - year: Year (integer).
        - category: Choose ONE from ['Gene Therapy', 'Cell & Immuno Therapy', 'Discovery & Targets', 'Clinical Translation', 'AI & Bioinformatics', 'Delivery Systems', 'Methodology & Tech', 'Safety & Toxicology'].
        - problem: The specific scientific bottleneck or gap addressed (The 'Why').
        - finding: The main conclusion or solution (The 'What').
        - method: Key techniques used (e.g., scRNA-seq, AAV evolution).
        
        Paper Text (truncated):
        {text_content[:30000]} 
        """
        
        response = model.generate_content(prompt)
        # 清洗数据，防止 AI 加 ```json 头
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        return {"error": str(e)}

def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages[:5]: # 读前5页通常足够提取摘要和结论
            text += page.extract_text()
        return text
    except:
        return None

# --- 3. UI Setup ---
st.set_page_config(page_title="BioBrain v1.0", layout="wide", page_icon="🧠")
st.markdown("""
<style>
    .main {background-color: #f8f9fa;}
    .stButton>button {width: 100%; border-radius: 8px; font-weight: bold;}
    .ai-button button {border: 2px solid #764ba2; color: #764ba2;}
</style>
""", unsafe_allow_html=True)

init_db()

st.title("🧠 BioBrain")
st.caption("AI-Powered Research Assistant | Engine: Gemini 2.5 Flash")

# --- 4. Sidebar ---
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("🔑 Gemini API Key", type="password")
    st.markdown("---")
    menu = st.radio("Navigation", ["📥 Log New Paper", "🔍 Problem Index"])

# --- Feature A: Log Paper ---
if menu == "📥 Log New Paper":
    st.header("📝 Log a New Discovery")
    
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {
            "title": "", "author": "", "year": 2026, "category": "Gene Therapy",
            "problem": "", "finding": "", "method": ""
        }
