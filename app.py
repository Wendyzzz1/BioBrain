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
        
        prompt = f"""
        Analyze this paper. Return JSON only.
        Keys: title, author, year, category (List), problem, finding, method.
        Text: {text_content[:30000]}
        """
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception as e:
        return {"error": str(e)}

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
            "problem": "", "finding": "", "method": ""
        }

    uploaded_file = st.file_uploader("Drop PDF here", type=["pdf"])

    if uploaded_file and st.button("🚀 Start Analysis"):
        with st.spinner("AI is reading..."):
            text = extract_text_from_pdf(uploaded_file)
            if text:
                data = analyze_with_gemini(text)
                if "error" in data:
                    st.error(data['error'])
                else:
                    # Compatibility check
                    if isinstance(data.get('category'), str):
                        data['category'] = [data['category']]
                    st.session_state.form_data.update(data)
                    st.success("✅ Analysis Complete!")

    with st.form("paper_form"):
        c1, c2 = st.columns(2)
        with c1:
            title = st.text_input("Title", value=st.session_state.form_data.get("title"))
            author = st.text_input("Author", value=st.session_state.form_data.get("author"))
            year = st.number_input("Year", value=int(st.session_state.form_data.get("year", 2026)))
            
            # Categories logic
            all_categories = ["Gene Therapy", "Cell Therapy", "Targets", "Clinical", "AI", "Methodology", "Review", "Neuroscience"]
            current_cats = st.session_state.form_data.get("category", [])
            if not isinstance(current_cats, list): current_cats = [str(current_cats)]
            
            # Split into presets and custom tags
            default_selection = [c for c in current_cats if c in all_categories]
            new_suggestions = [c for c in current_cats if c not in all_categories]
            
            selected_cats = st.multiselect("Categories (Preset)", all_categories, default=default_selection)
            
            extra_cats_str = ", ".join(new_suggestions)
            custom_tags = st.text_input("➕ Custom Tags (comma separated)", value=extra_cats_str, placeholder="e.g. Metabolism, Cancer")

        with c2:
            problem = st.text_area("Problem Solved", value=st.session_state.form_data.get("problem"), height=100)
            finding = st.text_area("Key Finding", value=st.session_state.form_data.get("finding"), height=100)
            method = st.text_input("Methodology", value=st.session_state.form_data.get("method"))
        
        if st.form_submit_button("💾 Save to Cloud"):
            # Merge tags
            final_tags = selected_cats
            if custom_tags:
                final_tags.extend([t.strip() for t in custom_tags.split(',') if t.strip()])
            final_tags = sorted(list(set(final_tags)))
            category_str = ", ".join(final_tags)

            # Get current time
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

            new_data = pd.DataFrame([{
                "date_added": current_time,
                "title": title, "author": author, "year": year, 
                "category": category_str,
                "problem_solved": problem, 
                "key_finding": finding, "methodology": method, "rating": 4
            }])
            
            with st.spinner("Saving to Google Sheets..."):
                if save_data(new_data):
                    st.success(f"✅ Saved! Date Added: {current_time}")

elif menu == "Library":
    st.subheader("📚 Library")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
    
    df = get_data()

    if not df.empty:
        # Ensure date_added exists for old data
        if "date_added" not in df.columns:
            df["date_added"] = "2024-01-01 00:00"

        df['category'] = df['category'].astype(str)
        # Sort: Newest date_added first
        df_sorted = df.sort_values(by="date_added", ascending=False)

        # Extract all unique tags
        all_tags = set()
        for cat_str in df['category']:
            tags = [t.strip() for t in cat_str.split(',') if t.strip()]
            all_tags.update(tags)
        sorted_tags = sorted(list(all_tags))

        # Create Tabs
        tabs = st.tabs(["🕒 Timeline"] + sorted_tags)

        # Tab 1: Timeline View
        with tabs[0]:
            st.caption("Sorted by Date Added (Newest First)")
            st.dataframe(
                df_sorted, 
                use_container_width=True,
                column_config={
                    "date_added": "Date Added",
                    "rating": st.column_config.NumberColumn("Rating", format="%d ⭐"),
                    "year": st.column_config.NumberColumn("Year", format="%d"),
                    "category": "Tags"
                }
            )

        # Tab 2+: Category Views
        for i, tag in enumerate(sorted_tags):
            with tabs[i+1]:
                # Filter rows containing the tag
                filtered_df = df_sorted[df_sorted['category'].str.contains(tag, regex=False, case=False)]
                st.info(f"📂 Papers tagged '{tag}': {len(filtered_df)}")
                st.dataframe(
                    filtered_df, 
                    use_container_width=True,
                    column_config={
                        "date_added": "Date Added",
                        "year": st.column_config.NumberColumn("Year", format="%d")
                    }
                )
    else:
        st.info("Library is empty. Go to 'Log Paper' to add your first entry!")
