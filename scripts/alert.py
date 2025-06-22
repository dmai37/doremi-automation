import smtplib
from email.message import EmailMessage
import email_credentials

def send_message(subject, body, to_email):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = email_credentials.EMAIL_ADDRESS
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email_credentials.EMAIL_ADDRESS, email_credentials.EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    send_message("Test Alert", "Hello World", "maitiendat7701@gmail.com")
    