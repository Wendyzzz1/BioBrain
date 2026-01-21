import streamlit as st
import sqlite3
import pandas as pd
import PyPDF2
import google.generativeai as genai
import json

# --- 1. Database Functions ---
def get_connection():
    return sqlite3.connect("biobrain.db")

def init_db():
    conn = get_connection()
    c = conn.cursor()
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

# --- 2. Real AI Processing ---
def analyze_with_gemini(api_key, text_content):
    """
    Sends the PDF text to Google Gemini and asks for a JSON response.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        You are an expert scientific researcher. Analyze the following academic paper text and extract key information.
        Return the output purely as a valid JSON object with no markdown formatting.
        
        The JSON keys must be exactly:
        - title: The full title of the paper.
        - author: The last name of the first author (e.g., 'Smith et al.').
        - year: The publication year (integer).
        - category: Choose ONE from ['Gene Therapy', 'Cell & Immuno Therapy', 'Discovery & Targets', 'Clinical Translation', 'AI & Bioinformatics', 'Delivery Systems', 'Methodology & Tech', 'Safety & Toxicology'].
        - problem: A concise summary of the specific scientific problem or bottleneck this paper addresses (The 'Why').
        - finding: The key conclusion or solution proposed (The 'What').
        - method: The primary methodologies used (e.g., scRNA-seq, CRISPR screen).
        
        Paper Text (truncated):
        {text_content[:30000]} 
        """
        
        response = model.generate_content(prompt)
        # Clean up code blocks if the AI adds them
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        return {"error": str(e)}

def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        # Read first 5 pages (usually enough for Intro + Discussion)
        for page in pdf_reader.pages[:5]:
            text += page.extract_text()
        return text
    except:
        return None

# --- 3. Page Setup ---
st.set_page_config(page_title="BioBrain AI", layout="wide", page_icon="🧠")
st.markdown("""
<style>
    .main {background-color: #f8f9fa;}
    .stButton>button {width: 100%; border-radius: 8px; font-weight: bold;}
    .ai-button button {border: 2px solid #764ba2; color: #764ba2;}
</style>
""", unsafe_allow_html=True)

# Initialize DB
init_db()

st.title("🧠 BioBrain v1.0")
st.caption("AI-Powered Research Assistant | Powered by Gemini Pro")

# --- 4. Sidebar & API Key ---
with st.sidebar:
    st.header("⚙️ Configuration")
    # 这里是输入钥匙的地方
    api_key = st.text_input("🔑 Enter Gemini API Key", type="password", help="Get one for free at aistudio.google.com")
    
    st.markdown("---")
    menu = st.radio("Navigation", ["📥 Log New Paper", "🔍 Problem Index"])

# --- Feature A: Log New Paper ---
if menu == "📥 Log New Paper":
    st.header("📝 Log a New Discovery")
    
    # Session State for form
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {
            "title": "", "author": "", "year": 2024, "problem": "", 
            "finding": "", "method": "", "category": "Gene Therapy"
        }

    # Upload
    uploaded_file = st.file_uploader("Upload PDF Paper", type=["pdf"])

    if uploaded_file:
        st.markdown('<div class="ai-button">', unsafe_allow_html=True)
        if st.button("✨ Analyze with Gemini AI"):
            if not api_key:
                st.error("⚠️ Please enter your API Key in the sidebar first!")
            else:
                with st.spinner("🤖 Reading paper & extracting insights..."):
                    # 1. Extract Text
                    raw_text = extract_text_from_pdf(uploaded_file)
                    if raw_text:
                        # 2. Call Real AI
                        ai_data = analyze_with_gemini(api_key, raw_text)
                        
                        if "error" in ai_data:
                            st.error(f"AI Error: {ai_data['error']}")
                        else:
                            # 3. Fill Form
                            st.session_state.form_data.update(ai_data)
                            st.success("✅ Analysis Complete!")
                    else:
                        st.error("Could not read PDF text.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    
    # Form
    with st.form("data_form"):
        c1, c2 = st.columns(2)
        with c1:
            title = st.text_input("Title", value=st.session_state.form_data.get("title", ""))
            author = st.text_input("First Author", value=st.session_state.form_data.get("author", ""))
            year = st.number_input("Year", value=int(st.session_state.form_data.get("year", 2024)))
            
            # Smart Category Selection
            cat_list = ['Gene Therapy', 'Cell & Immuno Therapy', 'Discovery & Targets', 'Clinical Translation', 'AI & Bioinformatics', 'Delivery Systems', 'Methodology & Tech', 'Safety & Toxicology']
            curr_cat = st.session_state.form_data.get("category", "Gene Therapy")
            cat_idx = cat_list.index(curr_cat) if curr_cat in cat_list else 0
            category = st.selectbox("Category", cat_list, index=cat_idx)
            
        with c2:
            problem = st.text_area("❓ Problem Solved", value=st.session_state.form_data.get("problem", ""), height=100)
            finding = st.text_area("💡 Key Finding", value=st.session_state.form_data.get("finding", ""), height=100)
            method = st.text_input("🔬 Methodology", value=st.session_state.form_data.get("method", ""))
            rating = st.slider("Rating", 1, 5, 4)
            
        if st.form_submit_button("💾 Save to Database"):
            conn = get_connection()
            conn.execute('INSERT INTO papers (title, first_author, year, category, problem_solved, key_finding, methodology, rating) VALUES (?,?,?,?,?,?,?,?)', 
                         (title, author, year, category, problem, finding, method, rating))
            conn.commit()
            conn.close()
            st.success(f"Saved: {title}")

# --- Feature B: Library ---
elif menu == "🔍 Problem Index":
    st.header("📚 Your Library")
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM papers ORDER BY id DESC", conn)
        for _, row in df.iterrows():
            with st.expander(f"📌 {row['problem_solved']}"):
                st.markdown(f"**{row['title']}** ({row['year']})")
                st.info(f"Finding: {row['key_finding']}")
                st.caption(f"Category: {row['category']} | Tech: {row['methodology']}")
    except:
        st.info("No papers yet.")
    conn.close()
