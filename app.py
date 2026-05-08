from flask import Flask, request, send_file
from flask import render_template, redirect, url_for
import pandas as pd
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
import json
import os

app = Flask(__name__)

# ================= GOOGLE SHEETS SETUP =================

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

google_creds = json.loads(os.environ.get("GOOGLE_CREDS_JSON"))

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    google_creds,
    scope
)

client = gspread.authorize(creds)

sheet = client.open("Naman Diagnostics Bookings").sheet1

# ================= LOAD TEST DATABASE =================

with open("tests.json", "r") as f:
    TESTS = json.load(f)

# ================= TWILIO SETUP =================

ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

twilio_client = Client(ACCOUNT_SID, AUTH_TOKEN)

# CHANGE THIS
ADMIN_NUMBER = "whatsapp:+919420662107"

# ================= USER MEMORY =================

users = {}

# ================= SAVE BOOKING =================

def save_booking(name, test, date, slot, phone, address):

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sheet.append_row([
        name,
        test,
        date,
        slot,
        phone,
        address,
        "Pending",
        timestamp
    ])

# ================= ADMIN ALERT =================

def send_admin_alert(name, test, date, slot, phone, address):

    try:

        twilio_client.messages.create(
            from_='whatsapp:+14155238886',

            body=f'''
NEW BOOKING 🚨

Name: {name}
Test: {test}
Date: {date}
Time Slot: {slot}
Phone: {phone}
Address: {address}
''',

            to=ADMIN_NUMBER
        )

    except Exception as e:

        print("Admin alert failed:", e)

# ================= PDF REPORT =================

def create_pdf(name, test, date, slot, address):

    filename = f"{name.replace(' ', '_')}_report.pdf"

    doc = SimpleDocTemplate(
        filename,
        pagesize=letter
    )

    styles = getSampleStyleSheet()

    story = []

    title = Paragraph(
        "<b>NAMAN DIAGNOSTICS</b>",
        styles['Title']
    )

    story.append(title)
    story.append(Spacer(1, 20))

    details = f'''
    <b>Patient Name:</b> {name}<br/><br/>
    <b>Test:</b> {test}<br/><br/>
    <b>Date:</b> {date}<br/><br/>
    <b>Time Slot:</b> {slot}<br/><br/>
    <b>Address:</b> {address}<br/><br/>
    <b>Lab:</b> NAMAN DIAGNOSTICS<br/><br/>
    <b>Location:</b> Savedi, Ahilyanagar
    '''

    story.append(
        Paragraph(details, styles['BodyText'])
    )

    story.append(Spacer(1, 30))

    footer = Paragraph(
        "Thank you for choosing NAMAN DIAGNOSTICS.",
        styles['Italic']
    )

    story.append(footer)

    doc.build(story)

    return filename

# ================= SEND PDF =================

def send_pdf(phone, pdf_file):

    try:

        twilio_client.messages.create(
            from_='whatsapp:+14155238886',

            body='📄 Your booking report is attached.',

            media_url=[
                f'https://naman-diagnostics-bot.onrender.com/files/{pdf_file}'
            ],

            to=phone
        )

    except Exception as e:

        print("PDF sending failed:", e)

# ================= TEST INFO =================

def get_test_info(test_name):

    test_name = test_name.lower()

    if test_name in TESTS:

        data = TESTS[test_name]

        return f'''
🧪 TEST INFORMATION

Test: {test_name.upper()}

💰 Price: ₹{data['price']}

🍽 Fasting:
{data['fasting']}
'''

    return '''
Test available.

Please contact lab for details.
'''

# ================= MENU =================

def menu(lang):

    if lang == "mr":

        return '''
🏥 NAMAN DIAGNOSTICS

1. अपॉइंटमेंट बुक करा
2. टेस्ट माहिती
3. वेळ व पत्ता
4. स्टाफशी बोला

नंबर पाठवा.
'''

    return '''
🏥 NAMAN DIAGNOSTICS

1. Book Appointment
2. Test Information
3. Timing & Location
4. Talk to Human

Reply with number.
'''

# ================= FILE ROUTE =================

@app.route('/files/<filename>')
def files(filename):

    return send_file(filename)

# ================= WHATSAPP ROUTE =================


from twilio.twiml.messaging_response import MessagingResponse

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    response = MessagingResponse()

    response.message("Bot is working perfectly ✅")

    return str(response)


    # ================= FIRST MESSAGE =================

    if user not in users:

        users[user] = {
            "step": "language"
        }

        reply = '''
Welcome to NAMAN DIAGNOSTICS 🏥

Select Language / भाषा निवडा

1. English
2. मराठी
'''

    else:

        step = users[user]["step"]

        lang = users[user].get("lang", "en")

        # ================= LANGUAGE =================

        if step == "language":

            if msg == "1":

                users[user]["lang"] = "en"
                users[user]["step"] = "menu"

                reply = menu("en")

            elif msg == "2":

                users[user]["lang"] = "mr"
                users[user]["step"] = "menu"

                reply = menu("mr")

            else:

                reply = '''
Select Language / भाषा निवडा

1. English
2. मराठी
'''

        # ================= NAME =================

        elif step == "name":

            users[user]["name"] = msg

            users[user]["step"] = "test"

            reply = (
                "Enter test name:"
                if lang == "en"
                else "टेस्ट नाव लिहा:"
            )

        # ================= TEST =================

        elif step == "test":

            users[user]["test"] = msg

            users[user]["step"] = "home_collection"

            if lang == "mr":

                reply = '''
होम सॅम्पल कलेक्शन हवे आहे का?

1. हो
2. नाही
'''

            else:

                reply = '''
Do you want Home Sample Collection?

1. Yes
2. No
'''

        # ================= HOME COLLECTION =================

        elif step == "home_collection":

            if msg == "1":

                users[user]["home_collection"] = "Yes"

                users[user]["step"] = "address"

                reply = (
                    "Enter your home address:"
                    if lang == "en"
                    else "तुमचा पत्ता लिहा:"
                )

            elif msg == "2":

                users[user]["home_collection"] = "No"

                users[user]["address"] = "Lab Visit"

                users[user]["step"] = "date"

                reply = (
                    "Enter appointment date:"
                    if lang == "en"
                    else "तारीख लिहा:"
                )

            else:

                reply = (
                    "Reply with 1 or 2"
                    if lang == "en"
                    else "1 किंवा 2 पाठवा"
                )

        # ================= ADDRESS =================

        elif step == "address":

            users[user]["address"] = msg

            users[user]["step"] = "date"

            reply = (
                "Enter appointment date:"
                if lang == "en"
                else "तारीख लिहा:"
            )

        # ================= DATE =================

        elif step == "date":

            users[user]["date"] = msg

            users[user]["step"] = "slot"

            if lang == "mr":

                reply = '''
वेळ निवडा:

1. सकाळी 7 - 9
2. सकाळी 9 - 12
3. दुपारी 12 - 3
4. दुपारी 3 - 6
5. संध्याकाळी 6 - 9
'''

            else:

                reply = '''
Select Time Slot:

1. 7 AM - 9 AM
2. 9 AM - 12 PM
3. 12 PM - 3 PM
4. 3 PM - 6 PM
5. 6 PM - 9 PM
'''

        # ================= SLOT =================

        elif step == "slot":

            slots = {
                "1": "7 AM - 9 AM",
                "2": "9 AM - 12 PM",
                "3": "12 PM - 3 PM",
                "4": "3 PM - 6 PM",
                "5": "6 PM - 9 PM"
            }

            slot = slots.get(msg)

            if not slot:

                reply = (
                    "Please select valid slot number (1-5)."
                    if lang == "en"
                    else "कृपया योग्य स्लॉट नंबर निवडा (1-5)."
                )

            else:

                users[user]["slot"] = slot

                data = users[user]

                # SAVE BOOKING

                save_booking(
                    data["name"],
                    data["test"],
                    data["date"],
                    data["slot"],
                    user,
                    data["address"]
                )

                # CREATE PDF

                pdf_file = create_pdf(
                    data['name'],
                    data['test'],
                    data['date'],
                    data['slot'],
                    data['address']
                )

                # SEND ADMIN ALERT

                send_admin_alert(
                    data["name"],
                    data["test"],
                    data["date"],
                    data["slot"],
                    user,
                    data["address"]
                )

                # SEND PDF

                send_pdf(user, pdf_file)

                # CONFIRMATION

                if lang == "mr":

                    reply = f'''
✅ अपॉइंटमेंट बुक झाले

👤 नाव:
{data['name']}

🧪 टेस्ट:
{data['test']}

📅 तारीख:
{data['date']}

🕒 वेळ:
{data['slot']}

📍 पत्ता:
{data['address']}

🏥 Naman Diagnostics
Savedi, Ahilyanagar

📄 PDF रिपोर्ट पाठवला आहे.
'''

                else:

                    reply = f'''
✅ APPOINTMENT BOOKED

👤 Name:
{data['name']}

🧪 Test:
{data['test']}

📅 Date:
{data['date']}

🕒 Time Slot:
{data['slot']}

📍 Address:
{data['address']}

🏥 Naman Diagnostics
Savedi, Ahilyanagar

📄 PDF report has been sent.
'''

                users[user]["step"] = "menu"

        # ================= TEST INFO =================

        elif step == "test_info":

            reply = get_test_info(msg)

            users[user]["step"] = "menu"

        # ================= MAIN MENU =================

        elif step == "menu" and msg == "1":

            users[user]["step"] = "name"

            reply = (
                "Enter your name:"
                if lang == "en"
                else "तुमचे नाव लिहा:"
            )

        elif step == "menu" and msg == "2":

            users[user]["step"] = "test_info"

            reply = (
                "Enter test name:"
                if lang == "en"
                else "टेस्ट नाव लिहा:"
            )

        elif step == "menu" and msg == "3":

            if lang == "mr":

                reply = '''
🏥 NAMAN DIAGNOSTICS

📍 Meenu Bunglow,
Professor Colony Chowk Rd,
near SBI ATM,
Savedi, Ahilyanagar,
Maharashtra 414003

🕖 वेळ:
सकाळी 7 ते रात्री 9
'''

            else:

                reply = '''
🏥 NAMAN DIAGNOSTICS

📍 Meenu Bunglow,
Professor Colony Chowk Rd,
near SBI ATM,
Savedi, Ahilyanagar,
Maharashtra 414003

🕖 Timing:
7:00 AM to 9:00 PM
'''

        elif step == "menu" and msg == "4":

            reply = (
                "Our staff will contact you shortly."
                if lang == "en"
                else "आमचा स्टाफ लवकरच संपर्क करेल."
            )

        # ================= DEFAULT =================

        else:

            reply = menu(lang)

    # ================= SEND RESPONSE =================

    resp = MessagingResponse()

    resp.message(reply)

    return str(resp)

# ================= ADMIN DASHBOARD =================

@app.route('/admin')
def admin_dashboard():

    records = sheet.get_all_records()

    return render_template(
        'dashboard.html',
        bookings=records
    )

# ================= RUN APP =================

if __name__ == "__main__":

    app.run(port=5000)