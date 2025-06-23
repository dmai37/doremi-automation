import requests
import textbelt_key

def send_sms(phone, message):
    resp = requests.post('https://textbelt.com/text', {
        'phone': phone,
        'message': message,
        'key': textbelt_key.key  # My personal Textbelt key. The free tier allows 1 SMS per day, but is disabled in the US due to abuse.
    })
    result = resp.json()
    if result['success']:
        print(f"SMS sent to {phone}")
    else:
        print(f"Failed to send SMS to {phone}: {result['error']}")

def send_reminders():
    with open('contacts.txt', 'r') as f:
        contacts = [line.strip() for line in f if line.strip()]
    
    for contact in contacts:
        phone, email = contact.split(',')
        message = f"Your invoice has been sent to your email: {email}"
        send_sms(phone, message)

if __name__ == "__main__":
    send_reminders()