import pandas as pd

def clean_phone(phone):
    phone = ''.join(filter(str.isdigit, phone))
    if len(phone) == 10:
        phone = '+1' + phone
    elif len(phone) == 11 and phone.startswith('1'):
        phone = '+' + phone
    else:
        return None
    return phone

def extract_contacts(excel_file):
    df = pd.read_excel(excel_file)
    
    contacts = []
    phones = []
    emails = []
    for index, row in df.iterrows():
        phone = clean_phone(str(row['Phone']))
        email = row['Email']
        if phone and email:
            contacts.append(f"{phone},{email}")
            phones.append(phone)
            emails.append(email)
    
    with open('contacts.txt', 'w') as f:
        for contact in contacts:
            f.write(f"{contact}\n")
    
    with open('emails.txt', 'w') as f:
        for email in emails:
            f.write(f"{email}\n")
    
    print("Contacts extracted and saved to contacts.txt and emails.txt")

if __name__ == "__main__":
    extract_contacts('sample.xlsx')