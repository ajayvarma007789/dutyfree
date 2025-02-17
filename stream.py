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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import base64
from time import time

def load_templates():
    try:
        with open("templates.json", "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        st.error("❌ templates.json file is missing or invalid!")
        st.stop()

def load_faculty_list():
    try:
        return pd.read_excel("facultylist.xlsx")
    except FileNotFoundError:
        st.error("❌ facultylist.xlsx file not found!")
        st.stop()

faculty_df = load_faculty_list()

def validate_date(date_obj):
    if not date_obj:
        return None
    return date_obj.strftime("%d-%m-%Y")

def validate_contact(number):
    return number if re.fullmatch(r"\d{10,12}", number) else None

def generate_ai_leave_letter(data, faculty_df):
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        return "❌ Error: Missing GROQ API Key!"
    
    client = Groq(api_key=api_key)
    
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
    
    if 'additional_students' in data and len(data.get('additional_students', [])) > 2:
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

        Format it professionally with a polite tone in 2-3 paragraphs as it is given to college and include proper closing with Thanking you and Yours faithfully. Don't mention the other students in the letter body. In the closing section, mention only the main student's name without department and college name.
        """
    else:
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

        Format it professionally with a polite tone in 2-3 paragraphs as it is given to college and include proper closing with Thanking you and Yours faithfully. In the closing section, mention only the main student's name without department and college name.
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

def chat_interface():
    st.title("💬 DutyFree\nGenerate your apolegy/leave letter within 30sec.\n An AI tool for SJCET Students")

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
        "👥 Do you want to add more students to this letter?"
    ]

    fields = ["user", "programme", "department", "subto", "year_of_study", "start_date", "end_date", "add_students"] 

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

        if field_name == "add_students":
            user_choice = st.radio("👥 Do you want to add more students to this letter?", ["No", "Yes"], key="add_students_radio")
            
            if user_choice == "Yes":
                st.write("Enter additional students' details:")
                num_students = st.number_input("Number of additional students", min_value=1, max_value=5, value=1)
                
                additional_students = []
                for i in range(num_students):
                    st.write(f"Student {i+1}")
                    name = st.text_input(f"Name", key=f"student_name_{i}")
                    year = st.selectbox(f"Year of Study", 
                                      ["1st Year", "2nd Year", "3rd Year", "4th Year"] 
                                      if st.session_state.leave_data.get("programme") == "B.Tech" 
                                      else ["1st Year", "2nd Year"],
                                      key=f"student_year_{i}")
                    if name and year:
                        additional_students.append({"name": name, "year": year})

            cols = st.columns([1, 1, 1, 5])
            with cols[0]:
                if st.button("⬅️ Back", key="add_students_back_btn"): 
                    go_back()
                    st.rerun()
            with cols[2]:
                if st.button("Next ➡️", key="next_add_students"):
                    if user_choice == "Yes" and additional_students:
                        st.session_state.leave_data["additional_students"] = additional_students
                    st.session_state.messages.append({"role": "user", "text": f"Additional students: {user_choice}"})
                    st.session_state.step += 1
                    st.rerun()

        elif st.session_state.step > 0:
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

        elif field_name in ["start_date", "end_date"]:
            if field_name == "start_date":
                min_date = datetime.now() - timedelta(days=30) 
                max_date = datetime.now() + timedelta(days=365) 
            else:
                start_date = datetime.strptime(st.session_state.leave_data.get("start_date", datetime.now().strftime("%d-%m-%Y")), "%d-%m-%Y")
                min_date = start_date
                max_date = start_date + timedelta(days=365)
            
            if not any(msg["text"] == questions[st.session_state.step] for msg in st.session_state.messages):
                st.session_state.messages.append({"role": "assistant", "text": questions[st.session_state.step]})
                st.rerun()
            
            date_container = st.container()
            
            with date_container:
                date_value = st.date_input(
                    "",
                    min_value=min_date.date() if isinstance(min_date, datetime) else min_date,
                    max_value=max_date.date() if isinstance(max_date, datetime) else max_date,
                    key=f"{field_name}_calendar"
                )
                
                st.write("")
                
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
            if field_name != "add_students":  
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
        if user_input and field_name not in ["programme", "department", "subto", "year_of_study", "start_date", "end_date", "add_students"]: 
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

        # Main student signature
        signature_path = st.file_uploader("✍️ Upload your signature (optional)", type=["png", "jpg", "jpeg"], key="main_signature")
        
        # Additional students' signatures
        if 'additional_students' in st.session_state.leave_data:
            st.write("Upload signatures for additional students (optional):")
            signatures = {}
            for i, student in enumerate(st.session_state.leave_data['additional_students']):
                sig = st.file_uploader(
                    f"✍️ Upload signature for {student['name']} (optional)", 
                    type=["png", "jpg", "jpeg"],
                    key=f"signature_{i}"
                )
                if sig:
                    signatures[student['name']] = sig
            st.session_state.leave_data['additional_signatures'] = signatures

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
    
    template_data = {
        'user': data.get('user', ''),
        'year_of_study': data.get('year_of_study', ''),
        'programme': data.get('programme', ''),
        'department': data.get('department', ''),
        'start_date': data.get('start_date', ''),
        'end_date': data.get('end_date', ''),
        'current_date': current_date,
        'signature_date': current_date,
        'signature': '[Student Signature]',
        'subto': data.get('subto', '')
    }


    if data.get('subto') == "Principal":
        template_data['recipient_address'] = "The Principal\nSt. Joseph's College of Engineering and Technology\nPalai"
    else:
        faculty_info = faculty_df[faculty_df['Faculty'] == data['subto']]
        if not faculty_info.empty:
            template_data['recipient_address'] = f"{data['subto']}\n{faculty_info.iloc[0]['Designation']}\n{faculty_info.iloc[0]['Department']}\nSt. Joseph's College of Engineering and Technology\nPalai"
        else:
            template_data['recipient_address'] = f"{data['subto']}\nSt. Joseph's College of Engineering and Technology\nPalai"

    if 'additional_students' in data:
        additional_names = "\nAdditional students:\n"
        for student in data['additional_students']:
            additional_names += f"- {student['name']} ({student['year']})\n"
        if data.get('template') == "AI-generated":
            data['extra_details'] = f"{data.get('extra_details', '')}\n\n{additional_names}"
        else:
            template_data['additional_students'] = additional_names

    # Generate letter content
    if data.get('template') == "AI-generated":
        letter_content = generate_ai_leave_letter(data, faculty_df)
    else:
        try:
            template = templates.get(data['template'], '')
            if 'additional_students' in data:
                template_data['additional_students'] = "\nAdditional students:\n" + "\n".join([f"- {student['name']} ({student['year']})" for student in data['additional_students']])
            letter_content = template.format(**template_data)
        except KeyError as e:
            st.error(f"Template error: Missing field {e}")
            return
        except Exception as e:
            st.error(f"Error generating letter: {str(e)}")
            return

    def clean_text(text):
        cleaned = text.encode('ascii', 'ignore').decode('ascii')
        replacements = {
            '✅': 'X',
            '❌': 'X',
            '📝': '-',
            '👋': '-',
            '📚': '-',
            '🏢': '-',
            '📌': '-',
            '📅': '-',
            '👥': '-',
            '✍️': '-',
            '⬅️': '<-',
            '➡️': '->',
            '⏳': '-',
            '⚠️': '!',
            '📧': '-',
            '📥': '-'
        }
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        return cleaned

    letter_content = clean_text(letter_content)

    # PDF Generation
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Add the letter content
    pdf.multi_cell(0, 8, letter_content)
    
    if 'additional_students' in data:
        pdf.ln(10) 
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Student Details:", ln=True)
        pdf.ln(5)
        
        # Table settings
        col_widths = [70, 60, 60]
        row_height = 10
        
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(200, 200, 200) 
        
        pdf.cell(col_widths[0], row_height, "Name", 1, 0, 'C', 1)
        pdf.cell(col_widths[1], row_height, "Year of Study", 1, 0, 'C', 1)
        pdf.cell(col_widths[2], row_height, "Signature", 1, 1, 'C', 1)
        
        pdf.set_font("Arial", '', 10)
        
        pdf.cell(col_widths[0], row_height, data['user'], 1, 0, 'L')
        pdf.cell(col_widths[1], row_height, data['year_of_study'], 1, 0, 'C')
        sig_cell_y = pdf.get_y()
        pdf.cell(col_widths[2], row_height, "", 1, 1, 'C') 
        
        #main signature 
        if signature_path:
            signature_img = Image.open(signature_path)
            signature_img = signature_img.resize((50, 20), Image.LANCZOS)
            temp_path = "temp_signature.png"
            signature_img.save(temp_path)
            pdf.image(temp_path, x=pdf.get_x() + 145, y=sig_cell_y, w=30, h=8)
            os.remove(temp_path)
        
        for student in data['additional_students']:
            pdf.cell(col_widths[0], row_height, student['name'], 1, 0, 'L')
            pdf.cell(col_widths[1], row_height, student['year'], 1, 0, 'C')
            sig_cell_y = pdf.get_y()
            pdf.cell(col_widths[2], row_height, "", 1, 1, 'C')  # Empty cell for signature
            
            # Addl signatures
            if 'additional_signatures' in data and student['name'] in data['additional_signatures']:
                sig_path = data['additional_signatures'][student['name']]
                if sig_path:
                    sig_img = Image.open(sig_path)
                    sig_img = sig_img.resize((50, 20), Image.LANCZOS)
                    temp_path = f"temp_sig_{student['name']}.png"
                    sig_img.save(temp_path)
                    pdf.image(temp_path, x=pdf.get_x() + 145, y=sig_cell_y, w=30, h=8)
                    os.remove(temp_path)

    letter_content = letter_content.split("\n\nStudent Details:")[0]

    output_file = f"{data['user'].replace(' ', '_')}_leave_letter.pdf"
    pdf_data = pdf.output(dest='S').encode('latin1')

    # Store everything in session state
    if 'pdf_generated' not in st.session_state:
        st.session_state.pdf_data = pdf_data
        st.session_state.pdf_filename = output_file
        st.session_state.user_data = data
        st.session_state.pdf_generated = True
        st.session_state.generation_time = time()
        
    col1, col2 = st.columns(2)
    
    if data.get('template') == "AI-generated":
        col1, col2, col3 = st.columns(3)
    else:
        col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            "📥 Download Letter",
            st.session_state.pdf_data,
            file_name=st.session_state.pdf_filename,
            mime="application/pdf",
            key="download_btn"
        )
    
    with col2:
        if st.button("📧 Send to Copy Shop", key="email_btn"):
            success = send_to_copy_shop(
                st.session_state.pdf_data,
                st.session_state.pdf_filename,
                st.session_state.user_data['user'],
                st.session_state.user_data['department']
            )
            if success:
                st.success("✅ PDF sent to copy shop successfully!")
            else:
                st.error("❌ Failed to send PDF to copy shop")
    
    # Modify the regenerate button section inside generate_leave_letter function
    if data.get('template') == "AI-generated":
        with col3:
            if st.button("🔄 Regenerate Letter", key="regenerate_btn"):
                new_letter_content = generate_ai_leave_letter(data, faculty_df)
                
                # Create new PDF with the regenerated content
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.multi_cell(0, 8, clean_text(new_letter_content))
                
                # Add table if there are additional students
                if 'additional_students' in data:
                    pdf.ln(10)  
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 10, "Student Details:", ln=True)
                    pdf.ln(5)
                    
                    # Table settings
                    col_widths = [70, 60, 60]
                    row_height = 10
                    
                    pdf.set_font("Arial", 'B', 10)
                    pdf.set_fill_color(200, 200, 200)
                    
                    pdf.cell(col_widths[0], row_height, "Name", 1, 0, 'C', 1)
                    pdf.cell(col_widths[1], row_height, "Year of Study", 1, 0, 'C', 1)
                    pdf.cell(col_widths[2], row_height, "Signature", 1, 1, 'C', 1)
                    
                    pdf.set_font("Arial", '', 10)
                    
                    pdf.cell(col_widths[0], row_height, data['user'], 1, 0, 'L')
                    pdf.cell(col_widths[1], row_height, data['year_of_study'], 1, 0, 'C')
                    sig_cell_y = pdf.get_y()
                    pdf.cell(col_widths[2], row_height, "", 1, 1, 'C')
                    
                    # Add main signature if provided
                    if signature_path:
                        signature_img = Image.open(signature_path)
                        signature_img = signature_img.resize((50, 20), Image.LANCZOS)
                        temp_path = "temp_signature.png"
                        signature_img.save(temp_path)
                        pdf.image(temp_path, x=pdf.get_x() + 145, y=sig_cell_y, w=30, h=8)
                        os.remove(temp_path)
                    
                    # Add additional students
                    for student in data['additional_students']:
                        pdf.cell(col_widths[0], row_height, student['name'], 1, 0, 'L')
                        pdf.cell(col_widths[1], row_height, student['year'], 1, 0, 'C')
                        sig_cell_y = pdf.get_y()
                        pdf.cell(col_widths[2], row_height, "", 1, 1, 'C')
                        
                        # Add signature if available
                        if 'additional_signatures' in data and student['name'] in data['additional_signatures']:
                            sig_path = data['additional_signatures'][student['name']]
                            if sig_path:
                                sig_img = Image.open(sig_path)
                                sig_img = sig_img.resize((50, 20), Image.LANCZOS)
                                temp_path = f"temp_sig_{student['name']}.png"
                                sig_img.save(temp_path)
                                pdf.image(temp_path, x=pdf.get_x() + 145, y=sig_cell_y, w=30, h=8)
                                os.remove(temp_path)
                
                # Update session state with new PDF
                st.session_state.pdf_data = pdf.output(dest='S').encode('latin1')
                st.rerun()

    # timer display
    remaining_time = 180 - int(time() - st.session_state.generation_time)
    if remaining_time > 0:
        st.info(f"⏳ Session expires in: {remaining_time} seconds")
        st.info("⚠️ AI can make mistakes. Please review the letter before sending.")
        st.info("⚠️ Regenerate for a letter with new content")
    else:
        st.warning("⚠️ Session expired! Redirecting to start...")
        reset_app()
        return

    # status indicators
    if 'download_complete' in st.session_state:
        st.success("✅ Letter downloaded successfully!")
    
    if 'email_sent' in st.session_state:
        st.success("✅ Letter sent to copy shop!")

def send_to_copy_shop(pdf_data, filename, student_name, department):
    try:
        GMAIL_USER = os.getenv('GMAIL_USER')
        GMAIL_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
        COPY_SHOP_EMAIL = os.getenv('COPY_SHOP_EMAIL')

        # Create message
        message = MIMEMultipart()
        message['From'] = GMAIL_USER
        message['To'] = COPY_SHOP_EMAIL
        message['Subject'] = f'Leave Letter - {student_name} ({department})'

        body = f'Please find attached the leave letter for {student_name} from {department}.'
        message.attach(MIMEText(body, 'plain'))

        pdf_attachment = MIMEApplication(pdf_data, _subtype='pdf')
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename=filename)
        message.attach(pdf_attachment)

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        
        server.send_message(message)
        server.quit()
        return True

    except Exception as e:
        st.error(f"Error sending email: {str(e)}")
        return False
    
def reset_app():
    """Helper function to reset the application state"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

def main():
    if 'pdf_generated' not in st.session_state:
        faculty_df = load_faculty_list()
        leave_data, signature_path = chat_interface()
        if leave_data:
            generate_leave_letter(leave_data, load_templates(), faculty_df, signature_path)
    else:
        generate_leave_letter(
            st.session_state.user_data, 
            load_templates(), 
            load_faculty_list(), 
            None
        )

if __name__ == "__main__":
    main()

