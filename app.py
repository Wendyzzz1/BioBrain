import streamlit as st
import sqlite3
import pandas as pd
import PyPDF2
import google.generativeai as genai
import json

# --- Helper Functions ---
def get_connection():
    return sqlite3.connect("biobrain.db")

def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages[:5]:
            text += page.extract_text()
        return text
    except:
        return None

# --- Page Config ---
st.set_page_config(page_title="BioBrain Debugger", layout="wide", page_icon="🛠️")
st.markdown("""
<style>
    .main {background-color: #f8f9fa;}
    .stButton>button {width: 100%; border-radius: 8px;}
</style>
""", unsafe_allow_html=True)

st.title("🛠️ BioBrain 诊断模式")

# --- Sidebar ---
with st.sidebar:
    api_key = st.text_input("🔑 Gemini API Key", type="password")
    st.info("请填入 Key，然后点击右侧的 'Check Available Models'")

# --- Diagnostic Area ---
st.header("1. 模型自检 (Model Diagnostics)")

if st.button("🔍 Check Available Models (查看可用模型)"):
    if not api_key:
        st.error("请先在左侧填入 API Key")
    else:
        try:
            genai.configure(api_key=api_key)
            models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    models.append(m.name)
            st.success(f"✅ 连接成功！您的 Key 支持以下模型：\n\n" + "\n".join(models))
        except Exception as e:
            st.error(f"❌ 连接失败: {e}")

st.markdown("---")
st.header("2. 尝试分析 (Try Analysis)")
st.caption("我们将尝试使用列表中的第一个可用模型。")

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file and api_key and st.button("🚀 强制运行 (Force Run)"):
    try:
        genai.configure(api_key=api_key)
        # 自动选择最稳的一个模型
        model_name = 'models/gemini-1.5-flash' # 默认尝试
        
        # 这里的代码会尝试分析
        with st.spinner(f"正在尝试使用 {model_name}..."):
            model = genai.GenerativeModel(model_name)
            text = extract_text_from_pdf(uploaded_file)
            if text:
                response = model.generate_content(f"Summarize this scientific paper in 1 sentence:\n{text[:5000]}")
                st.success("🎉 成功了！AI 回复：")
                st.info(response.text)
            else:
                st.error("无法读取 PDF")
    except Exception as e:
        st.error(f"还是报错: {e}")
