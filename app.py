import streamlit as st
import pandas as pd
import sqlite3
import json
import hashlib
from google import genai
from google.genai import types

st.set_page_config(page_title="AI Native Teacher Suite", layout="wide")

# ==========================================
# 1. DATABASE & STORAGE INITIALIZATION
# ==========================================
DB_FILE = "teacher_workspace.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates the internal storage tables if they don't exist yet."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users Table (For Authentication)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT
        )
    ''')
    
    # Students Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY,
            name TEXT,
            grade TEXT
        )
    ''')
    
    # Lessons Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            content TEXT
        )
    ''')
    
    # Worksheets Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS worksheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            content TEXT
        )
    ''')
    
    # Grades Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            task_name TEXT,
            mark INTEGER,
            feedback TEXT
        )
    ''')
    
    # Pre-populate a default teacher account (Password: admin123) if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        default_hash = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("admin", default_hash))
        
    conn.commit()
    conn.close()

# Run the database setup immediately
init_db()

# ==========================================
# 2. AUTHENTICATION SYSTEM ENGINE
# ==========================================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def login_user(username, password):
    target_hash = hashlib.sha256(password.encode()).hexdigest()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, target_hash))
    user = cursor.fetchone()
    conn.close()
    if user:
        st.session_state.authenticated = True
        st.session_state.username = username
        return True
    return False

# Show Login Interface if not logged in
if not st.session_state.authenticated:
    st.title("🧙‍♂️ AI Teacher Workspace Secure Login")
    with st.form("login_form"):
        user_input = st.text_input("Username", value="admin")
        pass_input = st.text_input("Password", type="password", help="Default password is: admin123")
        login_btn = st.form_submit_button("Access Workspace")
        
        if login_btn:
            if login_user(user_input, pass_input):
                st.success("Access Granted!")
                st.rerun()
            else:
                st.error("Invalid Username or Password configuration.")
    st.stop()

# ==========================================
# 3. AI CLIENT INITIALIZATION
# ==========================================
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error(f"Failed to initialize Gemini Client: {e}")
    st.info("Check that GEMINI_API_KEY is defined in your secrets.toml file.")
    st.stop()

# Initialize Session States for transient cross-tab operations
if 'active_lesson' not in st.session_state:
    st.session_state.active_lesson = ""
if 'active_worksheet' not in st.session_state:
    st.session_state.active_worksheet = ""

# Logout action in Sidebar
st.sidebar.title(f"👤 Welcome, {st.session_state.username}")
if st.sidebar.button("Log Out Securely"):
    st.session_state.authenticated = False
    st.rerun()

# Workspace Selector Navigation
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
    
    # Read Current Data directly from local storage file
    conn = get_db_connection()
    df_students = pd.read_sql_query("SELECT * FROM students", conn)
    conn.close()
    
    if not df_students.empty:
        st.subheader("Current Student Registry")
        st.dataframe(df_students, use_container_width=True, hide_index=True)
    else:
        st.info("No students registered yet in this built-in database.")
    
    with st.form("student_form", clear_on_submit=True):
        st.write("**Register New Student**")
        s_id = st.text_input("Unique Student ID Number")
        s_name = st.text_input("Full Name")
        s_grade = st.selectbox("Assign Grade Cohort", ["Grade 6", "Grade 7", "Grade 8", "High School"])
        submit = st.form_submit_button("Commit to Local Database")
        
        if submit and s_id and s_name:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO students (id, name, grade) VALUES (?, ?, ?)", (s_id, s_name, s_grade))
                conn.commit()
                conn.close()
                st.success(f"Successfully registered {s_name} into local storage!")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error(f"Student ID '{s_id}' already exists in your local roster record database.")

# ==========================================
# MODULE 2: AI LESSON ARCHITECT
# ==========================================
elif menu == "📝 AI Lesson Architect":
    st.header("AI Lesson Planning Studio")
    topic = st.text_input("Enter Curriculum Topic / Target Standards:", placeholder="e.g., Photosynthesis")
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

    if st.session_state.active_lesson:
        st.session_state.active_lesson = st.text_area(
            "Modify/Refine AI Lesson Output:", 
            st.session_state.active_lesson, 
            height=400
        )
        
        if st.button("Save Lesson Plan to Storage"):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO lessons (topic, content) VALUES (?, ?)", (topic, st.session_state.active_lesson))
            conn.commit()
            conn.close()
            st.success("Lesson design structural data permanently saved to local storage disk.")

# ==========================================
# MODULE 3: AI WORKSHEET FACTORY (With View Button Table!)
# ==========================================
elif menu == "📄 AI Worksheet Factory":
    st.header("AI Assessment & Worksheet Engine")
    
    # 1. GENERATE NEW WORKSHEET SECTION
    with st.expander("✨ Synthesize New Assignment Worksheet", expanded=not st.session_state.active_worksheet):
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

        if st.session_state.active_worksheet:
            st.session_state.active_worksheet = st.text_area(
                "Modify/Refine Assessment Sheet Items:", 
                st.session_state.active_worksheet, 
                height=300
            )
            
            if st.button("Save Worksheet File to Database Storage"):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO worksheets (topic, content) VALUES (?, ?)", (worksheet_topic, st.session_state.active_worksheet))
                conn.commit()
                conn.close()
                st.success(f"Worksheet file '{worksheet_topic}' securely saved to system files.")
                st.session_state.active_worksheet = ""
                st.rerun()

    st.markdown("---")
    
    # 2. IN-BUILT TABLE WITH INTERACTIVE "VIEW" BUTTONS
    st.subheader("🗄️ Saved Worksheets Vault")
    conn = get_db_connection()
    df_ws = pd.read_sql_query("SELECT id, topic, content FROM worksheets", conn)
    conn.close()
    
    if df_ws.empty:
        st.info("No worksheets saved in storage database records yet.")
    else:
        # Loop over items to display them in a clean row format with interactive buttons
        for idx, row in df_ws.iterrows():
            col1, col2, col3 = st.columns([1, 6, 2])
            with col1:
                st.write(f"**#{row['id']}**")
            with col2:
                st.write(row['topic'])
            with col3:
                # Custom target button for each individual row index assignment
                if st.button("📄 Inspect Worksheet", key=f"view_ws_{row['id']}"):
                    st.session_state.view_target_topic = row['topic']
                    st.session_state.view_target_content = row['content']
        
        # Pop open a reading card below the table if clicked
        if 'view_target_content' in st.session_state:
            st.markdown("---")
            st.subheader(f"🔍 Viewing Record: {st.session_state.view_target_topic}")
            st.text_area("File Print Preview View:", st.session_state.view_target_content, height=350)
            if st.button("Close Preview Pane"):
                del st.session_state.view_target_content
                st.rerun()

# ==========================================
# MODULE 4: AI AUTO-MARKING SYSTEM
# ==========================================
elif menu == "🎯 AI Auto-Marking System":
    st.header("AI Diagnostic Assessment Engine")
    
    conn = get_db_connection()
    df_students = pd.read_sql_query("SELECT * FROM students", conn)
    df_worksheets = pd.read_sql_query("SELECT * FROM worksheets", conn)
    conn.close()
    
    if df_students.empty or df_worksheets.empty:
        st.warning("Ensure active classroom rosters and worksheet templates are saved inside your system database first.")
    else:
        student_mapping = dict(zip(df_students['name'], df_students['id']))
        selected_student_name = st.selectbox("Select Student Submitting Work:", list(student_mapping.keys()))
        selected_worksheet = st.selectbox("Target Assignment Reference Key:", list(df_worksheets['topic']))
        
        criteria_text = df_worksheets[df_worksheets['topic'] == selected_worksheet]['content'].values[0]
        student_submission = st.text_area("Paste Student's Answers Here:", height=200)
        
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
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO grades (student_id, task_name, mark, feedback) 
                VALUES (?, ?, ?, ?)
            ''', (str(student_mapping[selected_student_name]), selected_worksheet, int(final_score), final_commentary))
            conn.commit()
            conn.close()
            st.balloons()
            st.success(f"Permanent score entry updated for {selected_student_name} inside local tables.")

# ==========================================
# MODULE 5: STUDENT PORTFOLIOS
# ==========================================
elif menu == "📊 Student Portfolios":
    st.header("Comprehensive Academic Performance Profiles")
    
    conn = get_db_connection()
    df_students = pd.read_sql_query("SELECT * FROM students", conn)
    df_grades = pd.read_sql_query("SELECT * FROM grades", conn)
    conn.close()
    
    if df_students.empty or df_grades.empty:
        st.info("No structural mark entries or logs found in the local database records system.")
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