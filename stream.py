import json
import re
import os
import streamlit as st
from datetime import datetime
from fpdf import FPDF
import requests
from groq import Groq

def load_templates():
    try:
        with open("templates.json", "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        st.error("Error: templates.json file is missing or contains invalid JSON!")
        st.stop()

def validate_date(date_str):
    try:
        datetime.strptime(date_str, "%d-%m-%Y")
        return date_str
    except ValueError:
        return None

def validate_contact_number(number):
    return number if re.fullmatch(r"\d{10,12}", number) else None

def generate_ai_leave_letter(data):
    """Generates a leave letter using Groq AI based on user input."""

    api_key = "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" 
    if not api_key:
        return "Error: Groq API key is missing! Please set the environment variable 'GROQ_API_KEY'."

    client = Groq(api_key="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")

    prompt = (
        f"Generate a professional leave letter for {data['user']} in {data['year_of_study']} year, {data['programme']} ({data['department']}). "
        f"The letter should be addressed to {data['subto']} requesting leave from {data['start_date']} to {data['end_date']}. "
        f"The reason for leave is: {data['extra_details']}. "
        f"Please format it formally with a polite tone. Include the contact number {data['contact_number']}."
    )

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an AI assistant that generates professional leave letters."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile"
        )

        return response.choices[0].message.content if response.choices else "Error: No response from AI."

    except Exception as e:
        return f"Error generating letter: {str(e)}"

def chat_interface():
    st.title("💬 Leave Letter Chatbot")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.step = 0
        st.session_state.leave_data = {}
    
    questions = [
        "👋 Hello! What's your name?",
        "📌 To whom is this letter addressed?",
        "🎓 What is your year of study?",
        "📚 What is your programme (e.g., BTech, MTech)?",
        "🏢 Which department are you in?",
        "📞 Enter your contact number:",
        "📅 Enter the start date of your leave (DD-MM-YYYY):",
        "📅 Enter the end date of your leave (DD-MM-YYYY):"
    ]
    
    fields = ["user", "subto", "year_of_study", "programme", "department", "contact_number", "start_date", "end_date"]
    
    for msg in st.session_state.messages:
        st.chat_message("assistant" if msg["role"] == "assistant" else "user").write(msg["text"])
    
    if st.session_state.step < len(questions):
        user_input = st.chat_input(questions[st.session_state.step])
        
        if user_input:
            field_name = fields[st.session_state.step]
            
            if field_name == "contact_number":
                user_input = validate_contact_number(user_input)
                if not user_input:
                    st.session_state.messages.append({"role": "assistant", "text": "❌ Invalid number!"})
                    st.rerun()
            
            if field_name in ["start_date", "end_date"]:
                user_input = validate_date(user_input)
                if not user_input:
                    st.session_state.messages.append({"role": "assistant", "text": "❌ Invalid date!"})
                    st.rerun()
            
            st.session_state.leave_data[field_name] = user_input
            st.session_state.messages.append({"role": "user", "text": user_input})
            st.session_state.step += 1
            
            if st.session_state.step < len(questions):
                st.session_state.messages.append({"role": "assistant", "text": questions[st.session_state.step]})
            
            st.rerun()
    else:
        templates = load_templates()
        choice = st.radio("Choose a template or AI-generated letter:", ["Template", "AI"], horizontal=True)
        
        if choice == "Template":
            selected_template = st.selectbox("📄 Select a template:", list(templates.keys()))
            st.session_state.leave_data["template"] = selected_template
        else:
            st.session_state.leave_data["template"] = "AI-generated"
            st.session_state.leave_data["extra_details"] = st.text_area("📝 Describe your reason:")
        
        signature_path = st.file_uploader("✍️ Upload signature (optional)", type=["png", "jpg", "jpeg"])
        if st.button("✅ Generate Leave Letter"):
            return st.session_state.leave_data, signature_path
    
    return None, None

def generate_leave_letter(data, templates, signature_path=None):
    if data['template'] == "AI-generated":
        letter_content = generate_ai_leave_letter(data)
    else:
        letter_content = templates.get(data['template'], "Dear {subto},\n\nI am {user} from {year_of_study} year, {programme} ({department}).\n\nReason: {extra_details}\n\nLeave: {start_date} to {end_date}\n\nThank you.").format(**data)
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, letter_content)
    
    if signature_path:
        with open("temp_signature.png", "wb") as f:
            f.write(signature_path.getbuffer())
        pdf.image("temp_signature.png", x=10, y=pdf.get_y() + 5, w=30)
    
    output_file = f"{data['user'].replace(' ', '_')}_leave_letter.pdf"
    pdf.output(output_file)
    
    with open(output_file, "rb") as file:
        st.download_button("📥 Download Leave Letter", file, file_name=output_file, mime="application/pdf")

def main():
    leave_data, signature_path = chat_interface()
    if leave_data:
        generate_leave_letter(leave_data, load_templates(), signature_path)

if __name__ == "__main__":
    main()
