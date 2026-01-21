import streamlit as st
import sqlite3
import pandas as pd
import PyPDF2
import google.generativeai as genai
import json

# --- Page Setup ---
st.set_page_config(page_title="BioBrain v3.0", layout="wide", page_icon="🧠")

# --- Database Functions ---
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
    except:
        pass
    finally:
        conn.close()

def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages[:5]:
            text += page.extract_text()
        return text
    except:
        return None

# --- AI Function (The Fix) ---
def analyze_with_gemini(api_key, text_content):
    try:
        genai.configure(api_key=api_key)
        
        # 1. 设置模型
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        # 2. 清洗 PDF 里的脏字符 (第一道防线)
        clean_content = text_content.encode('utf-8', 'ignore').decode('utf-8')
        
        prompt = f"""
        You are a research assistant. Extract data from this text.
        Response must be valid JSON.
        
        Keys needed:
        - title (string)
        - author (string)
        - year (integer)
        - category (string, choose from: Gene Therapy, Cell Therapy, Targets, Clinical, AI, Methodology)
        - problem (string)
        - finding (string)
        - method (string)

        Text:
        {clean_content[:30000]}
        """
        
        # 3. 开启“强制 JSON 模式” (第二道防线 - 核心修复)
        # 这会强制 AI 就算遇到脏字符，也要转义成合法的 JSON 格式
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        # 4. 解析结果
        return json.loads(response.text)
        
    except Exception as e:
        # 如果还是出错，返回错误信息给界面
        return {"error": f"JSON Parsing Error: {str(e)}"}

# --- Main App Logic ---
init_db()

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Gemini API Key", type="password")
    st.markdown("---")
    menu = st.radio("Menu", ["Log Paper", "Library"])

st.title("🧠 BioBrain")

if menu == "Log Paper":
    st.subheader("Upload PDF")
    
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {
            "title": "", "author": "", "year": 2026, "category": "Gene Therapy",
            "problem": "", "finding": "", "method": ""
        }

    uploaded_file = st.file_uploader("Drop PDF here", type=["pdf"])

    if uploaded_file:
        if st.button("Start Analysis"):
            if not api_key:
                st.error("Need API Key!")
            else:
                with st.spinner("Gemini is reading (JSON Mode)..."): 
                    text = extract_text_from_pdf(uploaded_file)
                    if text:
                        data = analyze_with_gemini(api_key, text)
                        if "error" in data:
                            st.error(data['error'])
                        else:
                            st.session_state.form_data.update(data)
                            st.success("Done!")
                    else:
                        st.error("PDF Read Error")

    st.markdown("---")
    with st.form("paper_form"):
        c1, c2 = st.columns(2)
        with c1:
            title = st.text_input("Title", value=st.session_state.form_data.get("title"))
            author = st.text_input("Author", value=st.session_state.form_data.get("author"))
            year = st.number_input("Year", value=int(st.session_state.form_data.get("year", 2026)))
            category = st.selectbox("Category", ["Gene Therapy", "Cell Therapy", "Targets", "Clinical", "AI", "Methodology"])
        with c2:
            problem = st.text_area("Problem", value=st.session_state.form_data.get("problem"))
            finding = st.text_area("Finding", value=st.session_state.form_data.get("finding"))
            method = st.text_input("Method", value=st.session_state.form_data.get("method"))
        
        if st.form_submit_button("Save"):
            conn = get_connection()
            conn.execute('INSERT INTO papers (title, first_author, year, category, problem_solved, key_finding, methodology, rating) VALUES (?,?,?,?,?,?,?,4)',
                         (title, author, year, category, problem, finding, method))
            conn.commit()
            conn.close()
            st.success("Saved!")

elif menu == "Library":
    st.subheader("Library")
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM papers ORDER BY id DESC", conn)
    conn.close()
    
    if not df.empty:
        for index, row in df.iterrows():
            with st.expander(f"{row['title']}"):
                st.write(f"**Problem:** {row['problem_solved']}")
                st.write(f"**Finding:** {row['key_finding']}")
    else:
        st.info("No papers yet.")
