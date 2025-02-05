import json
import os
import re
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from fpdf import FPDF
from dotenv import load_dotenv
from groq import Groq  
from PIL import Image
import io

# Load Templates
def load_templates():
    try:
        with open("templates.json", "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        st.error("❌ templates.json file is missing or invalid!")
        st.stop()

# Load Faculty List
def load_faculty_list():
    try:
        return pd.read_excel("facultylist.xlsx")
    except FileNotFoundError:
        st.error("❌ facultylist.xlsx file not found!")
        st.stop()

faculty_df = load_faculty_list()

# Validation Functions
def validate_date(date_obj):
    if not date_obj:
        return None
    return date_obj.strftime("%d-%m-%Y")

def validate_contact(number):
    return number if re.fullmatch(r"\d{10,12}", number) else None

# AI Leave Letter Generation
def generate_ai_leave_letter(data, faculty_df):
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        return "❌ Error: Missing GROQ API Key!"
    
    client = Groq(api_key=api_key)
    
    # Get faculty designation 
    faculty_designation = ""
    recipient_line = ""
    sir_madam = ""
    
    if data['subto'] == "Principal":
        recipient_line = "The Principal"
        sir_madam = "Sir/Madam"
    else:
        faculty_info = faculty_df[faculty_df['Faculty'] == data['subto']]
        if not faculty_info.empty:
            faculty_designation = faculty_info.iloc[0]['Designation']
            recipient_line = f"{data['subto']}\n{faculty_designation}\n{faculty_info.iloc[0]['Department']}"
            sir_madam = "Sir/Madam"
    
    # AI Prompt
    prompt = f"""
    Write a formal leave letter using the following format:

    From:
    {data['user']}
    {data['year_of_study']} {data['programme']} ({data['department']})
    St. Joseph's College of Engineering and Technology
    Palai

    To:
    {recipient_line}
    St. Joseph's College of Engineering and Technology
    Palai

    Date: [Current Date]
    Subject: 
    Respected {sir_madam},

    Request leave from {data['start_date']} to {data['end_date']}.
    Reason: {data['extra_details']}

    Format it professionally having 1-3 paragraphs with a polite tone as it is given to college and include proper closing with Thanking you and Yours faithfully.In the closing section, do not want to mention the department name and college name again.
    """
    
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You generate professional leave letters following standard academic letter writing formats."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile"
        )
        
        return response.choices[0].message.content if response.choices else "❌ AI Response Error!"
    except Exception as e:
        return f"❌ Error: {str(e)}"
#CSS for buttons
st.markdown("""
<style>
    .stButton button {
        width: 120px;  # Adjust width as needed
        white-space: nowrap;
        margin-right: 30px;
    }
</style>
""", unsafe_allow_html=True)

# Chat Interface Logic
def chat_interface():
    st.title("💬 SJCET Leave Letter Chatbot")

    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.step = 0
        st.session_state.leave_data = {}
        st.session_state.messages.append({"role": "assistant", "text": "👋 What's your name?"})

    questions = [
        "👋 What's your name?",
        "📚 Select your programme:",
        "🏢 Select your department:",
        "📌 To whom is this letter addressed?",
        "📚 Which year do you study?",
        "📅 Select the start date of your leave:",
        "📅 Select the end date of your leave:",
        "📞 Enter your contact number:"
    ]

    fields = ["user", "programme", "department", "subto", "year_of_study", "start_date", "end_date", "contact_number"]
    programme_options = ["B.Tech", "M.Tech"]

    for msg in st.session_state.messages:
        st.chat_message("assistant" if msg["role"] == "assistant" else "user").write(msg["text"])

    def go_back():
        if st.session_state.step > 0:
            if len(st.session_state.messages) >= 2:
                st.session_state.messages.pop()
                st.session_state.messages.pop()
            if fields[st.session_state.step - 1] in st.session_state.leave_data:
                del st.session_state.leave_data[fields[st.session_state.step - 1]]
            st.session_state.step -= 1
            st.session_state.messages.append({"role": "assistant", "text": questions[st.session_state.step]})

    if st.session_state.step < len(questions):
        field_name = fields[st.session_state.step]
        user_input = None

        if st.session_state.step > 0:
            cols = st.columns([1, 3, 1])
        
        if field_name == "user":
            user_input = st.chat_input("")
        
        elif field_name == "programme":
            user_input = st.radio(questions[st.session_state.step], programme_options, key="programme_radio")
            cols = st.columns([1, 1,1, 5])
            with cols[0]:
                if st.button("⬅️ Back", key="programme_back"):
                    go_back()
                    st.rerun()
            with cols[2]:
                if st.button("Next ➡️", key="programme_next"):
                    st.session_state.messages.append({"role": "user", "text": user_input})
                    st.session_state.leave_data[field_name] = user_input
                    st.session_state.step += 1
                    if st.session_state.step < len(questions):
                        st.session_state.messages.append({"role": "assistant", "text": questions[st.session_state.step]})
                    st.rerun()
        
        elif field_name == "department":
            selected_programme = st.session_state.leave_data.get("programme", "B.Tech")
            department_options = faculty_df[faculty_df['Programme'] == selected_programme]['Department'].unique().tolist()
            user_input = st.selectbox(questions[st.session_state.step], department_options, key="department_select")
            cols = st.columns([1, 1, 1, 5])
            with cols[0]:
                if st.button("⬅️ Back", key="department_back"):
                    go_back()
                    st.rerun()
            with cols[2]:
                if st.button("Next ➡️", key="department_next"):
                    st.session_state.messages.append({"role": "user", "text": user_input})
                    st.session_state.leave_data[field_name] = user_input
                    st.session_state.step += 1
                    if st.session_state.step < len(questions):
                        st.session_state.messages.append({"role": "assistant", "text": questions[st.session_state.step]})
                    st.rerun()

        elif field_name == "subto":
            recipient_type = st.radio("Select recipient:", ["Principal", "Faculty"], horizontal=True, key="recipient_radio")
            if recipient_type == "Principal":
                user_input = "Principal"
                cols = st.columns([1, 1, 1, 5])
                with cols[0]:
                    if st.button("⬅️ Back", key="principal_back"):
                        go_back()
                        st.rerun()
                with cols[2]:
                    if st.button("Next ➡️", key="principal_next"):
                        st.session_state.messages.append({"role": "user", "text": user_input})
                        st.session_state.leave_data[field_name] = user_input
                        st.session_state.step += 1
                        if st.session_state.step < len(questions):
                            st.session_state.messages.append({"role": "assistant", "text": questions[st.session_state.step]})
                        st.rerun()
            else:
                selected_department = st.session_state.leave_data.get("department", "")
                faculty_options = faculty_df[faculty_df['Department'] == selected_department]['Faculty'].tolist()
                selected_faculty = st.selectbox("📜 Select Faculty:", faculty_options, key="faculty_select")
                cols = st.columns([1, 1, 1, 5])
                with cols[0]:
                    if st.button("⬅️ Back", key="faculty_back"):
                        go_back()
                        st.rerun()
                with cols[2]:
                    if st.button("Next ➡️", key="faculty_next"):
                        st.session_state.messages.append({"role": "user", "text": selected_faculty})
                        st.session_state.leave_data[field_name] = selected_faculty
                        st.session_state.step += 1
                        if st.session_state.step < len(questions):
                            st.session_state.messages.append({"role": "assistant", "text": questions[st.session_state.step]})
                        st.rerun()

        elif field_name == "year_of_study":
            selected_programme = st.session_state.leave_data.get("programme", "B.Tech")
            year_options = ["1st Year", "2nd Year", "3rd Year", "4th Year"] if selected_programme == "B.Tech" else ["1st Year", "2nd Year"]
            user_input = st.radio(questions[st.session_state.step], year_options, key="year_radio")
            cols = st.columns([1, 1, 1, 5])
            with cols[0]:
                if st.button("⬅️ Back", key="year_back"):
                    go_back()
                    st.rerun()
            with cols[2]:
                if st.button("Next ➡️", key="year_next"):
                    st.session_state.messages.append({"role": "user", "text": user_input})
                    st.session_state.leave_data[field_name] = user_input
                    st.session_state.step += 1
                    if st.session_state.step < len(questions):
                        st.session_state.messages.append({"role": "assistant", "text": questions[st.session_state.step]})
                    st.rerun()

        # [Previous code remains the same until the date handling section]

        elif field_name in ["start_date", "end_date"]:
            if field_name == "start_date":
                min_date = datetime.now() - timedelta(days=30)  # One month ago
                max_date = datetime.now() + timedelta(days=365)  # Up to one year in future
            else:
                start_date = datetime.strptime(st.session_state.leave_data.get("start_date", datetime.now().strftime("%d-%m-%Y")), "%d-%m-%Y")
                min_date = start_date
                max_date = start_date + timedelta(days=365)
            
            if not any(msg["text"] == questions[st.session_state.step] for msg in st.session_state.messages):
                st.session_state.messages.append({"role": "assistant", "text": questions[st.session_state.step]})
                st.rerun()
            
            # Create a container for date selection
            date_container = st.container()
            
            # Calendar in full width
            with date_container:
                date_value = st.date_input(
                    "",
                    min_value=min_date.date() if isinstance(min_date, datetime) else min_date,
                    max_value=max_date.date() if isinstance(max_date, datetime) else max_date,
                    key=f"{field_name}_calendar"
                )
                
                # Add some spacing
                st.write("")
                
                # Navigation buttons in separate columns below
                col1, col2, col3 = st.columns([1, 0.1, 1])
                
                with col1:
                    if st.button("⬅️ Back", key=f"back_{field_name}"):
                        go_back()
                        st.rerun()
                
                with col3:
                    if st.button("Next ➡️", key=f"next_{field_name}"):
                        validated_date = validate_date(date_value)
                        if validated_date:
                            st.session_state.messages.append({"role": "user", "text": validated_date})
                            st.session_state.leave_data[field_name] = validated_date
                            st.session_state.step += 1
                            if st.session_state.step < len(questions):
                                st.session_state.messages.append({"role": "assistant", "text": questions[st.session_state.step]})
                            st.rerun()
        else:
            if not any(msg["text"] == questions[st.session_state.step] for msg in st.session_state.messages):
                st.session_state.messages.append({"role": "assistant", "text": questions[st.session_state.step]})
                st.rerun()
            
            cols = st.columns([1, 3, 1])
            with cols[0]:
                if st.button("⬅️ Back", key=f"back_{field_name}"):
                    go_back()
                    st.rerun()
            
            user_input = st.chat_input("")

        # Handle text input validation and progression
        if user_input and field_name not in ["programme", "department", "subto", "year_of_study", "start_date", "end_date"]:
            if field_name == "contact_number":
                user_input = validate_contact(user_input)
                if not user_input:
                    st.session_state.messages.append({"role": "assistant", "text": "❌ Invalid phone number!"})
                    st.rerun()

            st.session_state.leave_data[field_name] = user_input
            st.session_state.messages.append({"role": "user", "text": user_input})
            st.session_state.step += 1

            if st.session_state.step < len(questions):
                st.session_state.messages.append({"role": "assistant", "text": questions[st.session_state.step]})

            st.rerun()

    else:
        templates = load_templates()
        choice = st.radio("📄 Choose a template or AI-generated letter:", ["Template", "AI"], horizontal=True)

        if choice == "Template":
            selected_template = st.selectbox("📜 Select a template:", list(templates.keys()))
            st.session_state.leave_data["template"] = selected_template
        else:
            st.session_state.leave_data["template"] = "AI-generated"
            st.session_state.leave_data["extra_details"] = st.text_area("📝 Describe your reason:")

        signature_path = st.file_uploader("✍️ Upload signature (optional)", type=["png", "jpg", "jpeg"])
        
        cols = st.columns([1, 3, 1])
        with cols[0]:
            if st.button("⬅️ Back to Questions"):
                go_back()
                st.rerun()
        with cols[2]:
            if st.button("✅ Generate Leave Letter"):
                return st.session_state.leave_data, signature_path

    return None, None

def generate_leave_letter(data, templates, faculty_df, signature_path=None):
    current_date = datetime.now().strftime("%d-%m-%Y")
    
    # Prepare template data with additional placeholders
    template_data = {
        **data,
        'current_date': current_date,
        'signature_date': current_date,
        'signature': '[Student Signature]'  # Default placeholder
    }

    # Add faculty details if applicable
    if data['subto'] != "Principal":
        faculty_info = faculty_df[faculty_df['Faculty'] == data['subto']]
        template_data.update({
            'faculty_designation': faculty_info.iloc[0]['Designation'] if not faculty_info.empty else "",
            'faculty_department': faculty_info.iloc[0]['Department'] if not faculty_info.empty else ""
        })

    # Generate letter content
    if data['template'] == "AI-generated":
        letter_content = generate_ai_leave_letter(data, faculty_df)
    else:
        template = templates.get(data['template'])
        letter_content = template.format(**template_data)

    # PDF generation with signature handling
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Process signature
    if signature_path:
        signature_img = Image.open(signature_path)
        signature_img = signature_img.resize((50, 100), Image.LANCZOS)
        signature_img.save("temp_signature.png")
        
        # Replace signature placeholder
        letter_content = letter_content.replace('[Student Signature]', '')

    # Write PDF content
    pdf.multi_cell(0, 8, letter_content)
    
    # Add signature image if uploaded
    if signature_path:
        pdf.image("temp_signature.png", x=10, y=pdf.get_y(), w=30, h=20)
        os.remove("temp_signature.png")

    # Generate and offer download
    output_file = f"{data['user'].replace(' ', '_')}_leave_letter.pdf"
    pdf.output(output_file)

    with open(output_file, "rb") as file:
        st.download_button("📥 Download Leave Letter", file, file_name=output_file, mime="application/pdf")
        
def main():
    faculty_df = load_faculty_list()  # Load faculty list at the start
    leave_data, signature_path = chat_interface()
    if leave_data:
        generate_leave_letter(leave_data, load_templates(), faculty_df, signature_path)

if __name__ == "__main__":
    main()