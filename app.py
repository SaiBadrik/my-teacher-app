import streamlit as st
import pandas as pd
from google import genai
from google.genai import types

st.set_page_config(page_title="AI Native Teacher Suite", layout="wide")
st.title("🧙‍♂️ AI-Native Teacher Workspace")
st.caption("Plan lessons, generate worksheets, and complete marking loops. Fully Editable & Free Cloud Saved.")

# ==========================================
# INITIALIZATION & DIRECT CSV FETCH
# ==========================================

# Initialize Gemini 2.5 Flash Client
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error(f"Failed to initialize Gemini Client: {e}")
    st.info("Check that GEMINI_API_KEY is defined in your secrets.toml file.")
    st.stop()

# Helper function to read tabs directly using your spreadsheet ID
def fetch_worksheet(sheet_name):
    sheet_id = "1lhl6c2WLaZBCxYxwrEhQMOhtdJL7O0-B7bRbvOY1T8k"
    # Appending &sheet= targets specific tabs (e.g., Students, Worksheets, Grades)
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={sheet_name}"
    
    try:
        return pd.read_csv(csv_url).dropna(how="all")
    except Exception as e:
        st.error(f"Could not load worksheet '{sheet_name}': {e}")
        st.info("Make sure your Google Sheet sharing options are set to 'Anyone with the link can view'.")
        return pd.DataFrame()

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
    
    # Form layout
    with st.form("student_form", clear_on_submit=True):
        st.write("**Register New Student**")
        s_id = st.text_input("Unique Student ID Number")
        s_name = st.text_input("Full Name")
        s_grade = st.selectbox("Assign Grade Cohort", ["Grade 6", "Grade 7", "Grade 8", "High School"])
        submit = st.form_submit_button("Commit to Database")
        
        if submit and s_id and s_name:
            st.warning("⚠️ Local view reading activated. To append new inputs directly into Google Sheets live, configure the st.connection cloud write pipeline.")

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

# ==========================================
# MODULE 4: AI AUTO-MARKING SYSTEM
# ==========================================
elif menu == "🎯 AI Auto-Marking System":
    st.header("AI Diagnostic Assessment Engine")
    
    # Pull Master Database dependencies
    df_students = fetch_worksheet("Students")
    df_worksheets = fetch_worksheet("Worksheets")
    
    if df_students.empty or df_worksheets.empty:
        st.warning("Ensure active rosters and worksheet master keys are populated in your cloud sheets first.")
    else:
        # User dropdown selections
        student_mapping = dict(zip(df_students['name'], df_students['id']))
        selected_student_name = st.selectbox("Select Student Submitting Work:", list(student_mapping.keys()))
        selected_worksheet = st.selectbox("Target Assignment Reference Key:", list(df_worksheets['topic']))
        
        # Pull associated criteria text
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
                
                # Parse JSON clean metrics
                import json
                try:
                    eval_metrics = json.loads(response.text)
                    st.session_state.ai_grade_suggestion = int(eval_metrics.get("grade", 0))
                    st.session_state.ai_feedback_suggestion = str(eval_metrics.get("feedback", ""))
                except Exception as json_err:
                    st.error(f"Failed to parse AI response: {json_err}")

        # FULLY EDITABLE EVALUATION CRITERIA FOR THE TEACHER OVERRIDE
        st.subheader("Teacher Verification Interface")
        final_score = st.slider("Verify/Modify Evaluated Mark (0-10):", 0, 10, value=st.session_state.ai_grade_suggestion)
        final_commentary = st.text_area("Verify/Rewrite Diagnostic Student Feedback:", value=st.session_state.ai_feedback_suggestion, height=150)

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