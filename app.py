import streamlit as st
import sqlite3
import pandas as pd
import PyPDF2
import time
import os

# --- Database & Helper Functions ---
def get_connection():
    # 使用当前目录下的数据库文件
    return sqlite3.connect("biobrain.db")

def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        # Read only the first 2 pages to save time/tokens
        for page in pdf_reader.pages[:2]:
            text += page.extract_text()
        return text
    except Exception as e:
        return None

# --- Page Config ---
st.set_page_config(page_title="BioBrain AI", layout="wide", page_icon="🧠")
st.markdown("""
<style>
    .main {background-color: #f8f9fa;}
    .stButton>button {width: 100%; border-radius: 8px; font-weight: bold;}
    .ai-button button {border: 2px solid #764ba2; color: #764ba2;}
</style>
""", unsafe_allow_html=True)

st.title("🧠 BioBrain")
st.caption("AI-Powered Research Assistant | From PDF to Knowledge in Seconds.")

# --- Sidebar ---
with st.sidebar:
    st.header("📍 Navigation")
    menu = st.radio("", ["📥 Log New Paper (AI)", "🔍 Problem Index", "📊 Dashboard"])
    st.markdown("---")
    st.info("v0.2 (Cloud Edition)")

# --- Feature A: Log New Paper ---
if menu == "📥 Log New Paper (AI)":
    st.header("📝 Log a New Discovery")
    uploaded_file = st.file_uploader("Drop your PDF here", type=["pdf"])
    
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {
            "title": "", "author": "", "problem": "", 
            "finding": "", "method": "", "category": "Gene Therapy"
        }

    if uploaded_file is not None:
        st.markdown('<div class="ai-button">', unsafe_allow_html=True)
        if st.button("✨ Auto-Extract Info with AI"):
            with st.spinner("🤖 AI is reading..."):
                # Simulated AI Response
                time.sleep(1.0)
                st.session_state.form_data = {
                    "title": "AAV-mediated gene therapy for Hemophilia A",
                    "author": "Pasi et al.",
                    "category": "Gene Therapy",
                    "problem": "High doses of AAV vectors cause hepatotoxicity and immune responses.",
                    "finding": "Novel promoter 'LP-1' reduced viral dose by 5-fold while maintaining efficacy.",
                    "method": "In vivo mouse model, qPCR"
                }
                st.success("Analysis Complete!")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    with st.form("new_paper_form"):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Paper Title", value=st.session_state.form_data["title"])
            first_author = st.text_input("First Author", value=st.session_state.form_data["author"])
            year = st.number_input("Year", min_value=1990, max_value=2030, value=2024)
            cat_options = ['Gene Therapy', 'Cell & Immuno Therapy', 'Discovery & Targets', 'Clinical Translation', 'AI & Bioinformatics', 'Methodology & Tech', 'Safety & Toxicology']
            try:
                cat_index = cat_options.index(st.session_state.form_data["category"])
            except:
                cat_index = 0
            category = st.selectbox("Category", cat_options, index=cat_index)
        with col2:
            problem = st.text_area("❓ Problem Solved", value=st.session_state.form_data["problem"], height=100)
            key_finding = st.text_area("💡 Key Finding", value=st.session_state.form_data["finding"])
            methodology = st.text_input("🔬 Methodology", value=st.session_state.form_data["method"])
            rating = st.slider("Rating", 1, 5, 4)

        if st.form_submit_button("💾 Save to BioBrain"):
            conn = get_connection()
            c = conn.cursor()
            try:
                # 自动建表，防止第一次运行没有表
                c.execute('''CREATE TABLE IF NOT EXISTS papers (id INTEGER PRIMARY KEY, title TEXT, first_author TEXT, year INTEGER, category TEXT, problem_solved TEXT, key_finding TEXT, methodology TEXT, rating INTEGER)''')
                
                # 插入数据
                c.execute('INSERT INTO papers (title, first_author, year, category, problem_solved, key_finding, methodology, rating) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', 
                          (title, first_author, year, category, problem, key_finding, methodology, rating))
                conn.commit()
                st.success(f"✅ Saved '{title}'")
            except Exception as e:
                st.error(f"Error saving to DB: {e}")
            finally:
                conn.close()

# --- Feature B: Problem Index ---
elif menu == "🔍 Problem Index":
    st.header("📚 Problem Index")
    conn = get_connection()
    try:
        # 确保表存在，防止报错
        conn.execute('''CREATE TABLE IF NOT EXISTS papers (id INTEGER PRIMARY KEY, title TEXT, first_author TEXT, year INTEGER, category TEXT, problem_solved TEXT, key_finding TEXT, methodology TEXT, rating INTEGER)''')
        
        df = pd.read_sql("SELECT * FROM papers ORDER BY id DESC", conn)
        if not df.empty:
            for i, row in df.iterrows():
                with st.expander(f"📌 {row['problem_solved']}"):
                    st.markdown(f"**{row['title']}**")
                    st.info(f"Finding: {row['key_finding']}")
        else:
            st.info("Library is empty. Go to 'Log New Paper' to add your first entry!")
    except Exception as e:
        st.error(f"Database Error: {e}")
    finally:
        conn.close()

elif menu == "📊 Dashboard":
    st.info("Dashboard stats coming soon.")
