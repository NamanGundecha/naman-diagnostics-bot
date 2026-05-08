from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json

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

ADMIN_NUMBER = "whatsapp:+919420662107"

# ================= USER MEMORY =================

users = {}

# ================= SAVE BOOKING =================

def save_booking(name, test, date, slot, phone):

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sheet.append_row([
        name,
        test,
        date,
        slot,
        phone,
        "Pending",
        timestamp
    ])

# ================= ADMIN ALERT =================

def send_admin_alert(name, test, date, slot, phone):

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
''',

            to=ADMIN_NUMBER
        )

    except Exception as e:

        print("Admin alert failed:", e)

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

# ================= MENUS =================

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

# ================= WHATSAPP ROUTE =================

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    msg = request.form.get("Body").strip()
    user = request.form.get("From")

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

        # ================= LANGUAGE SELECTION =================

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

        # ================= MAIN MENU =================

        elif msg == "1":

            users[user]["step"] = "name"

            reply = (
                "Enter your name:"
                if lang == "en"
                else "तुमचे नाव लिहा:"
            )

        elif msg == "2":

            users[user]["step"] = "test_info"

            reply = (
                "Enter test name:"
                if lang == "en"
                else "टेस्ट नाव लिहा:"
            )

        elif msg == "3":

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

        elif msg == "4":

            reply = (
                "Our staff will contact you shortly."
                if lang == "en"
                else "आमचा स्टाफ लवकरच संपर्क करेल."
            )

        # ================= TEST INFO =================

        elif step == "test_info":

            reply = get_test_info(msg)

            users[user]["step"] = "menu"

        # ================= BOOKING FLOW =================

        elif step == "name":

            users[user]["name"] = msg

            users[user]["step"] = "test"

            reply = (
                "Enter test name:"
                if lang == "en"
                else "टेस्ट नाव लिहा:"
            )

        elif step == "test":

            users[user]["test"] = msg

            users[user]["step"] = "date"

            reply = (
                "Enter appointment date:"
                if lang == "en"
                else "तारीख लिहा:"
            )

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

        elif step == "slot":

            slots = {
                "1": "7 AM - 9 AM",
                "2": "9 AM - 12 PM",
                "3": "12 PM - 3 PM",
                "4": "3 PM - 6 PM",
                "5": "6 PM - 9 PM"
            }

            slot = slots.get(msg, "Not Selected")

            users[user]["slot"] = slot

            data = users[user]

            # SAVE TO GOOGLE SHEETS
            save_booking(
                data["name"],
                data["test"],
                data["date"],
                data["slot"],
                user
            )

            # SEND ADMIN ALERT
            send_admin_alert(
                data["name"],
                data["test"],
                data["date"],
                data["slot"],
                user
            )

            # CONFIRMATION MESSAGE

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

📍 Naman Diagnostics
Savedi, Ahilyanagar

आमचा स्टाफ लवकरच संपर्क करेल.
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

📍 Naman Diagnostics
Savedi, Ahilyanagar

Our team will contact you shortly.
'''

            users[user]["step"] = "menu"

        # ================= HUMAN SUPPORT =================

        elif msg.lower() in ["human", "staff", "call"]:

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

# ================= RUN APP =================

if __name__ == "__main__":

    app.run(port=5000)