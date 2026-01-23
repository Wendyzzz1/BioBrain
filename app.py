import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import PyPDF2
import google.generativeai as genai
import json

# --- 1. Page Config ---
st.set_page_config(page_title="BioBrain Pro", layout="wide", page_icon="🧬")

# --- 2. Google Sheets Setup ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        return df
    except:
        return pd.DataFrame()

def save_data(new_row_df):
    try:
        existing_data = get_data()
        if existing_data.empty:
            updated_df = new_row_df
        else:
            updated_df = pd.concat([existing_data, new_row_df], ignore_index=True)
        
        conn.update(worksheet="Sheet1", data=updated_df)
        return True
    except Exception as e:
        st.error(f"Save Error: {str(e)}")
        return False

# --- 3. AI Helper ---
def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages[:5]:
            text += page.extract_text()
        return text
    except:
        return None

def analyze_with_gemini(api_key, text_content):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        # 修改点 1：提示词允许 AI 返回多个分类 (List of strings)
        prompt = f"""
        Analyze this paper. Return JSON only.
        Keys: 
        - title
        - author
        - year (integer)
        - category (List of strings. Select relevant ones from: Gene Therapy, Cell Therapy, Targets, Clinical, AI, Methodology, Review)
        - problem
        - finding
        - method

        Text: {text_content[:30000]}
        """
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception as e:
        return {"error": str(e)}

# --- 4. Main UI ---
st.title("🧬 BioBrain (Multi-Category)")
st.caption("Data saved to Google Drive | Engine: Gemini 2.5")

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Gemini API Key", type="password")
    menu = st.radio("Menu", ["Log Paper", "Library"])

if menu == "Log Paper":
    st.subheader("Upload PDF")
    
    # 修改点 2：初始化 category 为空列表 []，而不是字符串
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {
            "title": "", "author": "", "year": 2026, 
            "category": [],  # 变成列表
            "problem": "", "finding": "", "method": ""
        }

    uploaded_file = st.file_uploader("Drop PDF here", type=["pdf"])

    if uploaded_file and st.button("Start Analysis"):
        if not api_key:
            st.error("Need Gemini API Key!")
        else:
            with st.spinner("AI is reading..."):
                text = extract_text_from_pdf(uploaded_file)
                if text:
                    data = analyze_with_gemini(api_key, text)
                    if "error" in data:
                        st.error(data['error'])
                    else:
                        # 兼容性处理：防止 AI 偶尔抽风只返回字符串
                        if isinstance(data.get('category'), str):
                            data['category'] = [data['category']]
                        
                        st.session_state.form_data.update(data)
                        st.success("Analysis Done!")

    with st.form("paper_form"):
        c1, c2 = st.columns(2)
        with c1:
            title = st.text_input("Title", value=st.session_state.form_data.get("title"))
            author = st.text_input("Author", value=st.session_state.form_data.get("author"))
            year = st.number_input("Year", value=int(st.session_state.form_data.get("year", 2026)))
            
            # 修改点 3：变为 st.multiselect (多选框)
            all_categories = ["Gene Therapy", "Cell Therapy", "Targets", "Clinical", "AI", "Methodology", "Review", "Neuroscience"]
            
            # 确保 default 是一个列表，否则报错
            default_cats = st.session_state.form_data.get("category", [])
            if not isinstance(default_cats, list):
                default_cats = [str(default_cats)]
            # 过滤掉不在选项里的奇怪 tag，防止报错
            default_cats = [c for c in default_cats if c in all_categories]

            category = st.multiselect("Category (Multi-select)", all_categories, default=default_cats)

        with c2:
            problem = st.text_area("Problem", value=st.session_state.form_data.get("problem"))
            finding = st.text_area("Finding", value=st.session_state.form_data.get("finding"))
            method = st.text_input("Method", value=st.session_state.form_data.get("method"))
        
        if st.form_submit_button("Save to Cloud"):
            # 修改点 4：把列表变成字符串 (List -> String)
            # 例如: ["AI", "Gene Therapy"] -> "AI, Gene Therapy"
            category_str = ", ".join(category)

            new_data = pd.DataFrame([{
                "title": title, "author": author, "year": year, 
                "category": category_str, # 存字符串
                "problem_solved": problem, 
                "key_finding": finding, "methodology": method, "rating": 4
            }])
            
            with st.spinner("Saving..."):
                if save_data(new_data):
                    st.success("✅ Saved!")
                    st.balloons()

elif menu == "Library":
    st.subheader("📚 Library")
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        
    df = get_data()
    if not df.empty:
        st.dataframe(df)
    else:
        st.info("Empty.")
