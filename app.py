import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import PyPDF2
import google.generativeai as genai
import json

# --- 1. Page Config ---
st.set_page_config(page_title="BioBrain", layout="wide", page_icon="🧠")

# --- 2. Secret & Database Setup ---
# 自动读取 API Key (如果没有配置，会报错提醒)
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except FileNotFoundError:
    st.error("请在 Secrets 里配置 GEMINI_API_KEY")
    st.stop()

# 连接 Google Sheets
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

def analyze_with_gemini(text_content):
    try:
        # 直接使用全局变量 API_KEY
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        prompt = f"""
        Analyze this paper. Return JSON only.
        Keys: 
        - title
        - author
        - year (integer)
        - category (List of strings. Select from: Gene Therapy, Cell Therapy, Targets, Clinical, AI, Methodology, Review, Neuroscience)
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
st.title("🧠 BioBrain")
# 这里的 caption 也可以去掉了，因为不需要提示填 key
# st.caption("Engine: Gemini 2.5")

with st.sidebar:
    st.header("BioBrain Pro")
    # 输入框已经删除了！🚫
    st.success("✅ AI System Online") # 只要能读到 Key，就显示在线
    st.markdown("---")
    menu = st.radio("Menu", ["Log Paper", "Library"])

if menu == "Log Paper":
    st.subheader("Upload PDF")
    
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {
            "title": "", "author": "", "year": 2026, 
            "category": [],
            "problem": "", "finding": "", "method": ""
        }

    uploaded_file = st.file_uploader("Drop PDF here", type=["pdf"])

    # 按钮逻辑简化：不需要检查 if api_key 了，因为开头已经检查过了
    if uploaded_file and st.button("Start Analysis"):
        with st.spinner("AI is reading..."):
            text = extract_text_from_pdf(uploaded_file)
            if text:
                data = analyze_with_gemini(text) # 不需要传 key 了
                if "error" in data:
                    st.error(data['error'])
                else:
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
            
            all_categories = ["Gene Therapy", "Cell Therapy", "Targets", "Clinical", "AI", "Methodology", "Review", "Neuroscience"]
            default_cats = st.session_state.form_data.get("category", [])
            if not isinstance(default_cats, list): default_cats = [str(default_cats)]
            default_cats = [c for c in default_cats if c in all_categories]

            category = st.multiselect("Category", all_categories, default=default_cats)

        with c2:
            problem = st.text_area("Problem", value=st.session_state.form_data.get("problem"))
            finding = st.text_area("Finding", value=st.session_state.form_data.get("finding"))
            method = st.text_input("Method", value=st.session_state.form_data.get("method"))
        
        if st.form_submit_button("Save to Cloud"):
            category_str = ", ".join(category)
            new_data = pd.DataFrame([{
                "title": title, "author": author, "year": year, 
                "category": category_str,
                "problem_solved": problem, 
                "key_finding": finding, "methodology": method, "rating": 4
            }])
            
            with st.spinner("Saving..."):
                if save_data(new_data):
                    st.success("✅ Saved!")

elif menu == "Library":
    st.subheader("📚 Library")
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        
    df = get_data()
    if not df.empty:
        st.dataframe(df)
    else:
        st.info("Empty.")
