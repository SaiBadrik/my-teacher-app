import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="AI Native Teacher Suite", layout="wide")
st.title("🧙‍♂️ AI-Native Teacher Workspace")
st.caption("Plan lessons, generate worksheets, and complete marking loops. Fully Editable & Free Cloud Saved.")

# ==========================================
# INITIALIZATION & DIRECT GOOGLE SHEETS PIPELINE
# ==========================================

# Initialize Gemini 2.5 Flash Client
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error(f"Failed to initialize Gemini Client: {e}")
    st.stop()

# Direct Google Sheets Authentication Helper
@st.cache_resource
def get_gspread_client():
    # Define the required permissions scopes for Google Drive and Sheets
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        # Pull configurations cleanly out of your existing [connections.gsheets] block
        creds_dict = {
            "type": st.secrets["type"],
            "project_id": st.secrets["connections"]["gsheets"]["project_id"],
            "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
            "private_key": st.secrets["connections"]["gsheets"]["private_key"],
            "client_email": st.secrets["connections"]["gsheets"]["client_email"],
            "client_id": st.secrets["connections"]["gsheets"]["client_id"],
        }
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(credentials)
    except Exception as auth_err:
        st.error(f"Failed to authenticate with Google: {auth_err}")
        st.info("Check that your secrets.toml file matches the expected structure.")
        st.stop()

# Connect to your specific workbook
SPREADSHEET_ID = "1lhl6c2WLaZBCxYxwrEhQMOhtdJL7O0-B7bRbvOY1T8k"

def fetch_worksheet(sheet_name):
    gc = get_gspread_client()
    try:
        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sh.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Tab named '{sheet_name}' was not found in your Google Sheet!")
        st.info("Please make sure you have a tab named exactly matching that wording at the bottom of your sheet.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error reading '{sheet_name}': {e}")
        return pd.DataFrame()

def update_worksheet(sheet_name, df):
    gc = get_gspread_client()
    try:
        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sh.worksheet(sheet_name)
        worksheet.clear()
        # Include headers and write data rows back to the cloud
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        return True
    except Exception as e:
        st.error(f"Failed to save data to cloud: {e}")
        return False

# Initialize Session States for cross-tab workflows
if 'active_lesson' not in st.session_state:
    st.session_state.active_lesson = ""
if 'active_worksheet' not in st.session_state:
    st.session_state.active_worksheet = ""

# Sidebar Navigation Mode
menu = st.sidebar.radio("Workspace Selection", [
    "👥 Manage Students", 
    "📝 AI Lesson Architect", 
    "📄 AI Worksheet Factory", 
    "🎯 AI Auto-Marking System",
    "📊 Student Portfolios"
])

# ==========================================
# MODULE 1: MANAGE STUDENTS
# ==========================================
if menu == "👥 Manage Students":
    st.header("Classroom Roster Administration")
    
    # Read Current Data
    df_students = fetch_worksheet("Students")
    
    if not df_students.empty:
        st.subheader("Current Student Registry")
        st.dataframe(df_students, use_container_width=True)
    
    # Form layout to write data live to the sheet
    with st.form("student_form", clear_on_submit=True):
        st.write("**Register New Student**")
        s_id = st.text_input("Unique Student ID Number")
        s_name = st.text_input("Full Name")
        s_grade = st.selectbox("Assign Grade Cohort", ["Grade 6", "Grade 7", "Grade 8", "High School"])
        submit = st.form_submit_button("Commit to Database")
        
        if submit and s_id and s_name:
            new_student = pd.DataFrame([{"id": s_id, "name": s_name, "grade": s_grade}])
            updated_df = pd.concat([df_students, new_student], ignore_index=True)
            
            # Live Write Back to Cloud Sheet
            if update_worksheet("Students", updated_df):
                st.success(f"Successfully registered {s_name} into database!")
                st.rerun()

# ==========================================
# MODULE 2: AI LESSON ARCHITECT
# ==========================================
elif menu == "📝 AI Lesson Architect":
    st.header("AI Lesson Planning Studio")
    topic = st.text_input("Enter Curriculum Topic / Target Standards:", placeholder="e.g., Photosynthesis and Cellular Respiration")
    grade_focus = st.selectbox("Target Cohort Level:", ["Elementary", "Middle School", "High School"])
    
    if st.button("Generate Pedagogical Plan", type="primary"):
        with st.spinner("AI is architecting your 5E structured lesson layout..."):
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"Generate a robust, comprehensively structured 5E lesson plan for {grade_focus} covering: {topic}.",
                config=types.GenerateContentConfig(
                    system_instruction="You are an Elite Curriculum Instruction Designer. Output using explicit Markdown layouts.",
                    temperature=0.7
                )
            )
            st.session_state.active_lesson = response.text

    # FULLY EDITABLE OUTPUT BOX
    if st.session_state.active_lesson:
        st.session_state.active_lesson = st.text_area(
            "Modify/Refine AI Lesson Output:", 
            st.session_state.active_lesson, 
            height=400
        )
        
        if st.button("Save Lesson Plan to Cloud"):
            df_lessons = fetch_worksheet("Lessons")
            new_plan = pd.DataFrame([{"id": str(len(df_lessons)+1), "topic": topic, "content": st.session_state.active_lesson}])
            updated_df = pd.concat([df_lessons, new_plan], ignore_index=True)
            if update_worksheet("Lessons", updated_df):
                st.success("Lesson structural data permanently saved.")

# ==========================================
# MODULE 3: AI WORKSHEET FACTORY
# ==========================================
elif menu == "📄 AI Worksheet Factory":
    st.header("AI Assessment & Worksheet Engine")
    st.info("This engine references the lesson blueprint currently in session state context.")
    
    worksheet_topic = st.text_input("Name this Assessment Assignment File:")
    
    if st.button("Synthesize Worksheet from Lesson Context", type="primary"):
        if not st.session_state.active_lesson:
            st.warning("Please construct or paste a foundational lesson design context inside the Lesson Tab first.")
        else:
            with st.spinner("Compiling customized evaluation assignments..."):
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"Context: {st.session_state.active_lesson}\nTask: Generate a student worksheet file containing 5 multiple choice and 3 short responses, plus an explicit Answer Key block.",
                    config=types.GenerateContentConfig(
                        system_instruction="You are an expert assessment writer. Generate ready-to-print learning worksheets."
                    )
                )
                st.session_state.active_worksheet = response.text

    # FULLY EDITABLE OUTPUT BOX
    if st.session_state.active_worksheet:
        st.session_state.active_worksheet = st.text_area(
            "Modify/Refine Assessment Sheet:", 
            st.session_state.active_worksheet, 
            height=400
        )
        
        if st.button("Save Worksheet File to Cloud"):
            df_worksheets = fetch_worksheet("Worksheets")
            new_ws = pd.DataFrame([{"id": str(len(df_worksheets)+1), "topic": worksheet_topic, "content": st.session_state.active_worksheet}])
            updated_df = pd.concat([df_worksheets, new_ws], ignore_index=True)
            if update_worksheet("Worksheets", updated_df):
                st.success("Worksheet file and answer keys securely saved.")

# ==========================================
# MODULE 4: AI AUTO-MARKING SYSTEM
# ==========================================
elif menu == "🎯 AI Auto-Marking System":
    st.header("AI Diagnostic Assessment Engine")
    
    df_students = fetch_worksheet("Students")
    df_worksheets = fetch_worksheet("Worksheets")
    
    if df_students.empty or df_worksheets.empty:
        st.warning("Ensure active rosters and worksheet master keys are populated in your cloud sheets first.")
    else:
        student_mapping = dict(zip(df_students['name'], df_students['id']))
        selected_student_name = st.selectbox("Select Student Submitting Work:", list(student_mapping.keys()))
        selected_worksheet = st.selectbox("Target Assignment Reference Key:", list(df_worksheets['topic']))
        
        criteria_text = df_worksheets[df_worksheets['topic'] == selected_worksheet]['content'].values[0]
        student_submission = st.text_area("Paste Student's Handwritten/Typed Text Output Answers Here:", height=200)
        
        if "ai_grade_suggestion" not in st.session_state:
            st.session_state.ai_grade_suggestion = 0
        if "ai_feedback_suggestion" not in st.session_state:
            st.session_state.ai_feedback_suggestion = ""
            
        if st.button("Run Diagnostic AI Analysis", type="primary"):
            with st.spinner("AI evaluating against saved master rubric parameters..."):
                analysis_prompt = f"""
                Master Worksheet & Answer Key: {criteria_text}
                Student Response: {student_submission}
                
                Evaluate the student work. Return an integer grade from 0 to 10 and construct constructive qualitative evaluation feedback.
                Format your response using JSON format matching this exact design structure:
                {{
                    "grade": integer_score_0_to_10,
                    "feedback": "string text commentary"
                }}
                """
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=analysis_prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                
                import json
                try:
                    eval_metrics = json.loads(response.text)
                    st.session_state.ai_grade_suggestion = int(eval_metrics.get("grade", 0))
                    st.session_state.ai_feedback_suggestion = str(eval_metrics.get("feedback", ""))
                except Exception as json_err:
                    st.error(f"Failed to parse AI response: {json_err}")

        st.subheader("Teacher Verification Interface")
        final_score = st.slider("Verify/Modify Evaluated Mark (0-10):", 0, 10, value=st.session_state.ai_grade_suggestion)
        final_commentary = st.text_area("Verify/Rewrite Diagnostic Student Feedback:", value=st.session_state.ai_feedback_suggestion, height=150)
        
        if st.button("Finalize Gradebook Submission"):
            df_grades = fetch_worksheet("Grades")
            new_grade_entry = pd.DataFrame([{
                "id": str(len(df_grades)+1),
                "student_id": str(student_mapping[selected_student_name]),
                "task_name": selected_worksheet,
                "mark": int(final_score),
                "feedback": final_commentary
            }])
            updated_df = pd.concat([df_grades, new_grade_entry], ignore_index=True)
            if update_worksheet("Grades", updated_df):
                st.balloons()
                st.success(f"Permanent score entry updated for {selected_student_name}.")

# ==========================================
# MODULE 5: STUDENT PORTFOLIOS
# ==========================================
elif menu == "📊 Student Portfolios":
    st.header("Comprehensive Academic Performance Profiles")
    df_students = fetch_worksheet("Students")
    df_grades = fetch_worksheet("Grades")
    
    if df_students.empty or df_grades.empty:
        st.info("No marks entries found or could be read from cloud logs.")
    else:
        student_mapping = dict(zip(df_students['name'], df_students['id']))
        target_profile = st.selectbox("Select Profile View Target Portfolio:", list(student_mapping.keys()))
        
        target_id = str(student_mapping[target_profile])
        df_grades['student_id'] = df_grades['student_id'].astype(str)
        
        student_history = df_grades[df_grades['student_id'] == target_id]
        
        if student_history.empty:
            st.warning("This student does not have any saved grades or feedback entries.")
        else:
            st.subheader(f"Academic Overview Summary: {target_profile}")
            avg_score = student_history['mark'].astype(float).mean()
            st.metric(label="Calculated Mean Workspace Performance Grade", value=f"{avg_score:.2f} / 10")
            
            st.write("**Evaluation Task History Log:**")
            for index, row in student_history.iterrows():
                with st.expander(f"📋 {row['task_name']} — Evaluated Mark Result: {row['mark']}/10"):
                    st.write(f"**Instructor Feedback Narrative:**")
                    st.info(row['feedback'])