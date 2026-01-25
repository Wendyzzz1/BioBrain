import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import PyPDF2
import google.generativeai as genai
import json
from datetime import datetime

# --- 1. Page Config ---
st.set_page_config(page_title="BioBrain", layout="wide", page_icon="🧠")

# --- 2. Secret & Database Setup ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except FileNotFoundError:
    st.error("Missing GEMINI_API_KEY in Secrets.")
    st.stop()

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
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        # 🔥 Update 1: Added 'limitation' to the prompt
        prompt = f"""
        Analyze this paper. Return JSON only.
        Keys: 
        - title
        - author
        - year (integer)
        - category (List)
        - problem (What problem is solved?)
        - finding (Key results?)
        - method (Methodology used?)
        - limitation (What are the limitations or unsolved issues mentioned?)

        Text: {text_content[:30000]}
        """
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception as e:
        return {"error": str(e)}

# --- Helper to display a single paper card ---
def display_paper_card(row):
    # This creates the expandable card UI
    # Header: Title (Year) [Tags]
    card_title = f"📄 {row['title']} ({int(row['year'])})"
    
    with st.expander(card_title):
        st.caption(f"**Author:** {row['author']} | **Added:** {row['date_added']}")
        st.markdown(f"🏷️ **Tags:** `{row['category']}`")
        st.divider()
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🎯 Problem & Finding")
            st.info(f"**Problem:** {row['problem_solved']}")
            st.success(f"**Finding:** {row['key_finding']}")
        
        with c2:
            st.markdown("#### 🛠️ Method & Limitation")
            st.warning(f"**Method:** {row['methodology']}")
            # Handle old data that might not have 'limitation' yet
            lim = row.get('limitation', 'N/A')
            if pd.isna(lim) or lim == "": lim = "Not specified"
            st.error(f"**Limitation:** {lim}")

# --- 4. Main UI ---
st.title("🧠 BioBrain")

with st.sidebar:
    st.header("BioBrain Pro")
    st.success("✅ AI System Online")
    st.markdown("---")
    menu = st.radio("Menu", ["Log Paper", "Library"])

if menu == "Log Paper":
    st.subheader("📝 Log New Paper")
    
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {
            "title": "", "author": "", "year": 2026, 
            "category": [],
            "problem": "", "finding": "", "method": "", 
            "limitation": "" # 🔥 Update 2: Init limitation
        }

    uploaded_file = st.file_uploader("Drop PDF here", type=["pdf"])

    if uploaded_file and st.button("🚀 Start Analysis"):
        with st.spinner("AI is analyzing (including limitations)..."):
            text = extract_text_from_pdf(uploaded_file)
            if text:
                data = analyze_with_gemini(text)
                if "error" in data:
                    st.error(data['error'])
                else:
                    if isinstance(data.get('category'), str):
                        data['category'] = [data['category']]
                    st.session_state.form_data.update(data)
                    st.success("✅ Analysis Complete!")

    with st.form("paper_form"):
        # Top Metadata
        c1, c2 = st.columns(2)
        with c1:
            title = st.text_input("Title", value=st.session_state.form_data.get("title"))
            author = st.text_input("Author", value=st.session_state.form_data.get("author"))
            year = st.number_input("Year", value=int(st.session_state.form_data.get("year", 2026)))
        
        with c2:
             # Categories logic
            all_categories = ["Gene Therapy", "Cell Therapy", "Targets", "Clinical", "AI", "Methodology", "Review", "Neuroscience"]
            current_cats = st.session_state.form_data.get("category", [])
            if not isinstance(current_cats, list): current_cats = [str(current_cats)]
            
            default_selection = [c for c in current_cats if c in all_categories]
            new_suggestions = [c for c in current_cats if c not in all_categories]
            
            selected_cats = st.multiselect("Categories", all_categories, default=default_selection)
            extra_cats_str = ", ".join(new_suggestions)
            custom_tags = st.text_input("➕ Custom Tags", value=extra_cats_str)

        st.markdown("---")
        
        # Detailed Content
        col_left, col_right = st.columns(2)
        
        with col_left:
            problem = st.text_area("🎯 Problem Solved", value=st.session_state.form_data.get("problem"), height=150)
            method = st.text_input("🛠️ Methodology", value=st.session
