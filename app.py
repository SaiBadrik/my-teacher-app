import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="AI Native Teacher Suite", layout="wide")
st.title("🧙‍♂️ AI-Native Teacher Workspace")
st.caption("Plan lessons, generate worksheets, and complete marking loops. Fully Editable & Free Cloud Saved.")

# Initialize Gemini 2.5 Flash Client
# Automatically extracts GEMINI_API_KEY from your secrets.toml file
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error(f"Failed to initialize Gemini Client: {e}")
    st.info("Check that GEMINI_API_KEY is defined in your secrets.toml file.")
    st.stop()

# --- MANUAL INJECTION BYPASS ---
# This forces Streamlit to read your configuration parameters explicitly 
# bypassing the automated discovery system that causes configuration errors.
try:
    conn = st.connection(
        "gsheets", 
        type=GSheetsConnection,
        spreadsheet=st.secrets["spreadsheet"],
        type_account=st.secrets["type"],
        project_id=st.secrets["project_id"],
        private_key_id=st.secrets["private_key_id"],
        private_key=st.secrets["private_key"],
        client_email=st.secrets["client_email"],
        client_id=st.secrets["client_id"]
    )
except Exception as e:
    st.error(f"Critical System Config Validation Failed: {e}")
    st.info("Please verify your `.streamlit/secrets.toml` file is in the correct directory and has the correct spelling.")
    st.stop()

# Helper function to read safely and bypass data caching when editing
def fetch_worksheet(sheet_name):
    return conn.read(worksheet=sheet_name, ttl=0).dropna(how="all")

# Initialize Session States for cross-tab editable workflows
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
    st.subheader("Current Student Registry")
    st.dataframe(df_students, use_container_width=True)
    
    # Write New Data via Form
    with st.form("student_form", clear_on_submit=True):
        st.write("**Register New Student**")
        s_id = st.text_input("Unique Student ID Number")
        s_name = st.text_input("Full Name")
        s_grade = st.selectbox("Assign Grade Cohort", ["Grade 6", "Grade 7", "Grade 8", "High School"])
        submit = st.form_submit_button("Commit to Database")
        
        if submit and s_id and s_name:
            new_student = pd.DataFrame([{"id": s_id, "name": s_name, "grade": s_grade}])
            updated_df = pd.concat([df_students, new_student], ignore_index=True)
            conn.update(worksheet="Students", data=updated_df)
            st.success(f"Successfully registered {s_name} into database.")
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
            conn.update(worksheet="Lessons", data=updated_df)
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
            conn.update(worksheet="Worksheets", data=updated_df)
            st.success("Worksheet file and answer keys securely saved.")

# ==========================================
# MODULE 4: TARGETED AI AUTO-MARKING SYSTEM
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
                eval_metrics = json.loads(response.text)
                st.session_state.ai_grade_suggestion = int(eval_metrics.get("grade", 0))
                st.session_state.ai_feedback_suggestion = str(eval_metrics.get("feedback", ""))

        # FULLY EDITABLE EVALUATION CRITERIA FOR THE TEACHER OVERRIDE
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
            conn.update(worksheet="Grades", data=updated_df)
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
        st.info("No marks entries have been compiled inside the cloud database records yet.")
    else:
        student_mapping = dict(zip(df_students['name'], df_students['id']))
        target_profile = st.selectbox("Select Profile View Target Portfolio:", list(student_mapping.keys()))
        
        target_id = str(student_mapping[target_profile])
        # Convert column types to string to ensure safe database indexing matches
        df_grades['student_id'] = df_grades['student_id'].astype(str)
        
        student_history = df_grades[df_grades['student_id'] == target_id]
        
        if student_history.empty:
            st.warning("This student does not have any saved grades or feedback entries in this academic cycle.")
        else:
            st.subheader(f"Academic Overview Summary: {target_profile}")
            avg_score = student_history['mark'].astype(float).mean()
            st.metric(label="Calculated Mean Workspace Performance Grade", value=f"{avg_score:.2f} / 10")
            
            st.write("**Evaluation Task History Log:**")
            for index, row in student_history.iterrows():
                with st.expander(f"📋 {row['task_name']} — Evaluated Mark Result: {row['mark']}/10"):
                    st.write(f"**Instructor Feedback Narrative:**")
                    st.info(row['feedback'])