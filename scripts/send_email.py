import smtplib
from email.message import EmailMessage
import email_credentials  # Contains personal credentials
import os
import pandas as pd

def send_email(email, invoice_path, student_name):
    msg = EmailMessage()
    msg['Subject'] = f"Invoice for {student_name}"
    msg['From'] = email_credentials.user
    msg['To'] = email
    msg.set_content(f"Please find the invoice for {student_name} attached.")

    if os.path.exists(invoice_path):
        with open(invoice_path, 'rb') as img_file:
            img_data = img_file.read()
            img_name = os.path.basename(invoice_path)
            msg.add_attachment(img_data, maintype='image', subtype='jpeg', filename=img_name)
    else:
        print(f"Invoice not found at {invoice_path}")
        return

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email_credentials.user, email_credentials.password)
            server.send_message(msg)
            print(f"Email sent to {email} for {student_name}")
    except Exception as e:
        print(f"Failed to send email to {email} for {student_name}: {e}")

def send_invoices():
    df = pd.read_excel('sample.xlsx')
    
    for index, row in df.iterrows():
        email = row['Email']
        first = row['First'].replace(' ', '_')
        last = row['Last'].replace(' ', '_')
        student_name = f"{row['First']} {row['Last']}"
        invoice_filename = f"{first}_{last}_invoice.jpg"
        invoice_path = os.path.join('invoices', invoice_filename)
        send_email(email, invoice_path, student_name)

if __name__ == "__main__":
    send_invoices()