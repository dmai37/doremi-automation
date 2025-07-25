import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import sqlite3
import datetime
import os
from fpdf import FPDF
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import requests
import json
import time

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Database setup
conn = sqlite3.connect('students.db')
cursor = conn.cursor()

# Check and add family_id column if it doesn't exist
cursor.execute('PRAGMA table_info(students)')
columns = [col[1] for col in cursor.fetchall()]
if 'family_id' not in columns:
    cursor.execute('ALTER TABLE students ADD COLUMN family_id TEXT')

cursor.execute('''CREATE TABLE IF NOT EXISTS students
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 family_id TEXT,
                 name TEXT,
                 deposit REAL,
                 signup_date TEXT,
                 dob TEXT,
                 parent_name TEXT,
                 phone TEXT,
                 email TEXT,
                 lesson_day TEXT,
                 teacher TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS invoices
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 student_id INTEGER,
                 month INTEGER,
                 year INTEGER,
                 FOREIGN KEY(student_id) REFERENCES students(id))''')
cursor.execute('''CREATE TABLE IF NOT EXISTS invoice_items
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 invoice_id INTEGER,
                 date TEXT,
                 quantity INTEGER,
                 rate REAL,
                 amount REAL,
                 description TEXT,
                 FOREIGN KEY(invoice_id) REFERENCES invoices(id))''')
conn.commit()

# Google Drive authentication
def authenticate_google_drive():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    return creds

# Load credentials
def load_credentials():
    try:
        return Credentials.from_authorized_user_file('token.json', SCOPES)
    except FileNotFoundError:
        return None

class EditInvoiceWindow(tk.Toplevel):
    def __init__(self, parent, invoice_id):
        super().__init__(parent)
        self.title("Edit Invoice")
        self.invoice_id = invoice_id
        
        # Load invoice items
        cursor.execute("SELECT * FROM invoice_items WHERE invoice_id=?", (invoice_id,))
        self.items = cursor.fetchall()
        
        # Treeview to display items
        self.tree = ttk.Treeview(self, columns=("Date", "Quantity", "Rate", "Amount", "Description"), show="headings")
        self.tree.heading("Date", text="Date")
        self.tree.heading("Quantity", text="Quantity")
        self.tree.heading("Rate", text="Rate")
        self.tree.heading("Amount", text="Amount")
        self.tree.heading("Description", text="Description")
        self.tree.pack(fill="both", expand=True)
        
        for item in self.items:
            self.tree.insert("", "end", values=(item[2], item[3], item[4], item[5], item[6]))
        
        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)
        add_button = ttk.Button(button_frame, text="Add Item", command=self.add_item)
        add_button.grid(row=0, column=0, padx=5)
        edit_button = ttk.Button(button_frame, text="Edit Item", command=self.edit_item)
        edit_button.grid(row=0, column=1, padx=5)
        delete_button = ttk.Button(button_frame, text="Delete Item", command=self.delete_item)
        delete_button.grid(row=0, column=2, padx=5)
        save_button = ttk.Button(button_frame, text="Save Invoice", command=self.save_invoice)
        save_button.grid(row=0, column=3, padx=5)
    
    def add_item(self):
        date = simpledialog.askstring("Add Item", "Date (YYYY-MM-DD):")
        quantity = simpledialog.askinteger("Add Item", "Quantity:")
        rate = simpledialog.askfloat("Add Item", "Rate:")
        amount = quantity * rate if quantity and rate else 0
        description = simpledialog.askstring("Add Item", "Description:")
        if date and quantity and rate:
            self.tree.insert("", "end", values=(date, quantity, rate, amount, description))
    
    def edit_item(self):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected)
            values = item['values']
            date = simpledialog.askstring("Edit Item", "Date (YYYY-MM-DD):", initialvalue=values[0])
            quantity = simpledialog.askinteger("Edit Item", "Quantity:", initialvalue=values[1])
            rate = simpledialog.askfloat("Edit Item", "Rate:", initialvalue=values[2])
            amount = quantity * rate if quantity and rate else 0
            description = simpledialog.askstring("Edit Item", "Description:", initialvalue=values[4])
            if date and quantity and rate:
                self.tree.item(selected, values=(date, quantity, rate, amount, description))
    
    def delete_item(self):
        selected = self.tree.selection()
        if selected:
            self.tree.delete(selected)
    
    def save_invoice(self):
        cursor.execute("DELETE FROM invoice_items WHERE invoice_id=?", (self.invoice_id,))
        for child in self.tree.get_children():
            values = self.tree.item(child)['values']
            cursor.execute('''INSERT INTO invoice_items 
                              (invoice_id, date, quantity, rate, amount, description) 
                              VALUES (?, ?, ?, ?, ?, ?)''',
                           (self.invoice_id, values[0], values[1], values[2], values[3], values[4]))
        conn.commit()
        messagebox.showinfo("Success", "Invoice updated successfully")
        self.destroy()

class AddStudentWindow(tk.Toplevel):
    def __init__(self, parent, student=None):
        super().__init__(parent)
        self.title("Add Student" if student is None else "Edit Student")
        self.student = student
        self.family_mode = tk.BooleanVar(value=False)
        self.num_students = tk.IntVar(value=1)
        
        # Family checkbox
        self.family_check = tk.Checkbutton(self, text="Part of a Family?", variable=self.family_mode, command=self.toggle_family_mode)
        self.family_check.grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        
        # Number of students input
        self.num_students_label = tk.Label(self, text="Number of Students in Family:")
        self.num_students_entry = tk.Entry(self, textvariable=self.num_students, state='disabled')
        self.num_students_entry.bind("<Return>", self.update_student_fields)
        
        # Student fields container
        self.student_fields_frame = tk.Frame(self)
        self.student_fields_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5)
        
        # Initial fields
        self.student_entries = []
        self.update_student_fields()  # Fixed from add_student_fields to update_student_fields
        
        # Save and Cancel buttons
        save_button = tk.Button(self, text="Save", command=self.save_student)
        save_button.grid(row=3, column=0, padx=5, pady=10)
        cancel_button = tk.Button(self, text="Cancel", command=self.destroy)
        cancel_button.grid(row=3, column=1, padx=5, pady=10)
        
        if student:
            self.family_check.config(state='disabled')
            self.family_mode.set(False)
            self.toggle_family_mode()
            # Populate fields with existing student data
            fields = [
                "Student Name:", "Deposit Amount:", "Sign-up Date (YYYY-MM-DD):", 
                "Date of Birth (YYYY-MM-DD):", "Parent Name:", "Phone Number:", 
                "Email:", "Day of Week Taking Lessons", "Teacher:"
            ]
            for i, field in enumerate(fields):
                self.student_entries[0][field].insert(0, student[i+1])  # Populate with student data

    def toggle_family_mode(self):
        if self.family_mode.get():
            self.num_students_label.grid(row=1, column=0, padx=5, pady=5)
            self.num_students_entry.grid(row=1, column=1, padx=5, pady=5)
            self.num_students_entry.config(state='normal')
        else:
            self.num_students_label.grid_remove()
            self.num_students_entry.grid_remove()
            self.num_students_entry.config(state='disabled')
            self.num_students.set(1)
            self.update_student_fields()

    def update_student_fields(self, event=None):
        for widget in self.student_fields_frame.winfo_children():
            widget.destroy()
        self.student_entries = []
        num = self.num_students.get() if self.family_mode.get() else 1
        for i in range(num):
            frame = tk.LabelFrame(self.student_fields_frame, text=f"Student {i+1}")
            frame.pack(fill="x", padx=5, pady=5)
            entries = {}
            fields = [
                "Student Name:", "Deposit Amount:", "Sign-up Date (YYYY-MM-DD):", 
                "Date of Birth (YYYY-MM-DD):", "Parent Name:", "Phone Number:", 
                "Email:", "Day of Week Taking Lessons", "Teacher:"
            ]
            for j, field in enumerate(fields):
                tk.Label(frame, text=field).grid(row=j, column=0, padx=5, pady=5)
                entry = tk.Entry(frame)
                entry.grid(row=j, column=1, padx=5, pady=5)
                entries[field] = entry
            self.student_entries.append(entries)

    def save_student(self):
        if self.student:  # Editing existing student
            entries = self.student_entries[0]
            data = {field: entry.get() for field, entry in entries.items()}
            if not all(data[field] for field in data):
                messagebox.showerror("Error", "All fields must be filled")
                return
            try:
                cursor.execute('''UPDATE students SET 
                                  name=?, deposit=?, signup_date=?, dob=?, parent_name=?, phone=?, email=?, lesson_day=?, teacher=?
                                  WHERE id=?''',
                               (data["Student Name:"], 
                                float(data["Deposit Amount:"]) if data["Deposit Amount:"] else 0.0,
                                data["Sign-up Date (YYYY-MM-DD):"], 
                                data["Date of Birth (YYYY-MM-DD):"],
                                data["Parent Name:"], 
                                data["Phone Number:"], 
                                data["Email:"],
                                data["Day of Week Taking Lessons"], 
                                data["Teacher:"], self.student[0]))
                conn.commit()
                messagebox.showinfo("Success", "Student updated successfully")
                self.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))
        else:  # Adding new student(s)
            if self.family_mode.get():
                family_id = str(int(time.time()))  # Unique family ID based on timestamp
                for entries in self.student_entries:
                    data = {field: entry.get() for field, entry in entries.items()}
                    if not all(data[field] for field in data):
                        messagebox.showerror("Error", "All fields must be filled")
                        return
                    try:
                        cursor.execute('''INSERT INTO students 
                                          (family_id, name, deposit, signup_date, dob, parent_name, phone, email, lesson_day, teacher) 
                                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                       (family_id, data["Student Name:"], 
                                        float(data["Deposit Amount:"]) if data["Deposit Amount:"] else 0.0,
                                        data["Sign-up Date (YYYY-MM-DD):"], 
                                        data["Date of Birth (YYYY-MM-DD):"],
                                        data["Parent Name:"], 
                                        data["Phone Number:"], 
                                        data["Email:"],
                                        data["Day of Week Taking Lessons"], 
                                        data["Teacher:"]))
                    except Exception as e:
                        messagebox.showerror("Error", str(e))
                        return
            else:
                entries = self.student_entries[0]
                data = {field: entry.get() for field, entry in entries.items()}
                if not all(data[field] for field in data):
                    messagebox.showerror("Error", "All fields must be filled")
                    return
                try:
                    cursor.execute('''INSERT INTO students 
                                      (name, deposit, signup_date, dob, parent_name, phone, email, lesson_day, teacher) 
                                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                   (data["Student Name:"], 
                                    float(data["Deposit Amount:"]) if data["Deposit Amount:"] else 0.0,
                                    data["Sign-up Date (YYYY-MM-DD):"], 
                                    data["Date of Birth (YYYY-MM-DD):"],
                                    data["Parent Name:"], 
                                    data["Phone Number:"], 
                                    data["Email:"],
                                    data["Day of Week Taking Lessons"], 
                                    data["Teacher:"]))
                except Exception as e:
                    messagebox.showerror("Error", str(e))
                    return
            conn.commit()
            messagebox.showinfo("Success", "Student(s) added successfully")
            self.destroy()

class StudentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DoReMi Student Management")
        
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        
        # Notebook (tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)
        
        # Students tab
        self.students_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.students_tab, text="Students")
        
        # Invoices tab
        self.invoices_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.invoices_tab, text="Invoices")
        
        # Setup tabs
        self.setup_students_tab()
        self.setup_invoices_tab()
    
    def setup_students_tab(self):
        self.students_tree = ttk.Treeview(self.students_tab, columns=("ID", "Name", "Lesson Day"), show="headings")
        self.students_tree.heading("ID", text="ID")
        self.students_tree.heading("Name", text="Name")
        self.students_tree.heading("Lesson Day", text="Lesson Day")
        self.students_tree.pack(fill="both", expand=True)
        
        button_frame = ttk.Frame(self.students_tab)
        button_frame.pack(pady=10)
        add_button = ttk.Button(button_frame, text="Add Student", command=self.add_student)
        add_button.grid(row=0, column=0, padx=5)
        edit_button = ttk.Button(button_frame, text="Edit Student", command=self.edit_student)
        edit_button.grid(row=0, column=1, padx=5)
        delete_button = ttk.Button(button_frame, text="Delete Student", command=self.delete_student)
        delete_button.grid(row=0, column=2, padx=5)
        
        self.load_students()
    
    def load_students(self):
        for item in self.students_tree.get_children():
            self.students_tree.delete(item)
        cursor.execute("SELECT id, name, lesson_day FROM students")
        for student in cursor.fetchall():
            self.students_tree.insert("", "end", values=student)
    
    def add_student(self):
        AddStudentWindow(self.root)
        self.load_students()
    
    def edit_student(self):
        selected = self.students_tree.selection()
        if selected:
            student_id = self.students_tree.item(selected)['values'][0]
            cursor.execute("SELECT * FROM students WHERE id=?", (student_id,))
            student = cursor.fetchone()
            AddStudentWindow(self.root, student)
            self.load_students()
    
    def delete_student(self):
        selected = self.students_tree.selection()
        if selected:
            student_id = self.students_tree.item(selected)['values'][0]
            cursor.execute("DELETE FROM students WHERE id=?", (student_id,))
            conn.commit()
            self.load_students()
    
    def setup_invoices_tab(self):
        self.invoices_tree = ttk.Treeview(self.invoices_tab, columns=("ID", "Student Name", "Month", "Year"), show="headings")
        self.invoices_tree.heading("ID", text="ID")
        self.invoices_tree.heading("Student Name", text="Student Name")
        self.invoices_tree.heading("Month", text="Month")
        self.invoices_tree.heading("Year", text="Year")
        self.invoices_tree.pack(fill="both", expand=True)
        
        button_frame = ttk.Frame(self.invoices_tab)
        button_frame.pack(pady=10)
        generate_button = ttk.Button(button_frame, text="Generate Invoices", command=self.generate_invoices)
        generate_button.grid(row=0, column=0, padx=5)
        edit_button = ttk.Button(button_frame, text="Edit Invoice", command=self.edit_invoice)
        edit_button.grid(row=0, column=1, padx=5)
        upload_button = ttk.Button(button_frame, text="Upload to Google Drive", command=self.upload_invoices)
        upload_button.grid(row=0, column=2, padx=5)
        send_button = ttk.Button(button_frame, text="Send SMS", command=self.send_sms)
        send_button.grid(row=0, column=3, padx=5)
        
        self.load_invoices()
    
    def load_invoices(self):
        for item in self.invoices_tree.get_children():
            self.invoices_tree.delete(item)
        cursor.execute('''SELECT i.id, s.name, i.month, i.year 
                          FROM invoices i 
                          JOIN students s ON i.student_id = s.id''')
        for invoice in cursor.fetchall():
            self.invoices_tree.insert("", "end", values=invoice)
    
    def generate_invoices(self):
        if messagebox.askyesno("Confirm", "Generate invoices for the current month?"):
            current_date = datetime.date.today()
            current_year = current_date.year
            current_month = current_date.month
            
            cursor.execute("SELECT id, lesson_day FROM students")
            students = cursor.fetchall()
            
            for student in students:
                student_id, lesson_day = student
                if lesson_day:
                    cursor.execute("SELECT id FROM invoices WHERE student_id=? AND month=? AND year=?", 
                                   (student_id, current_month, current_year))
                    existing = cursor.fetchone()
                    if existing:
                        continue
                    
                    invoice_id = self.create_invoice(student_id, current_month, current_year)
                    day_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
                    day_index = day_map[lesson_day]
                    dates = []
                    start_date = datetime.date(current_year, current_month, 1)
                    end_date = datetime.date(current_year, current_month + 1, 1) if current_month < 12 else datetime.date(current_year + 1, 1, 1)
                    current_day = start_date
                    
                    while current_day.weekday() != day_index:
                        current_day += datetime.timedelta(days=1)
                    
                    while current_day < end_date:
                        dates.append(current_day)
                        current_day += datetime.timedelta(days=7)
                    
                    for date in dates:
                        cursor.execute('''INSERT INTO invoice_items 
                                          (invoice_id, date, quantity, rate, amount, description) 
                                          VALUES (?, ?, ?, ?, ?, ?)''',
                                       (invoice_id, date.strftime('%Y-%m-%d'), 1, 30, 30, "Lesson"))
                    conn.commit()
            
            self.load_invoices()
            messagebox.showinfo("Success", "Invoices generated successfully")

    def create_invoice(self, student_id, month, year):
        cursor.execute("INSERT INTO invoices (student_id, month, year) VALUES (?, ?, ?)", 
                       (student_id, month, year))
        conn.commit()
        return cursor.lastrowid
    
    def edit_invoice(self):
        selected = self.invoices_tree.selection()
        if selected:
            invoice_id = self.invoices_tree.item(selected)['values'][0]
            EditInvoiceWindow(self.root, invoice_id)
            self.load_invoices()
    
    def upload_invoices(self):
        if not messagebox.askyesno("Confirm", "Upload all invoices to Google Drive?"):
            return
        
        creds = load_credentials()
        if not creds:
            creds = authenticate_google_drive()
        if not creds:
            messagebox.showerror("Error", "Google Drive authentication failed")
            return
        
        service = build('drive', 'v3', credentials=creds)
        os.makedirs('invoices', exist_ok=True)
        
        uploaded = False
        for invoice in self.invoices_tree.get_children():
            invoice_id = self.invoices_tree.item(invoice)['values'][0]
            student_name = self.invoices_tree.item(invoice)['values'][1]
            month = self.invoices_tree.item(invoice)['values'][2]
            year = self.invoices_tree.item(invoice)['values'][3]
            
            pdf = self.generate_pdf(invoice_id)
            file_name = f"invoice_{student_name}_{month}_{year}.pdf"
            file_path = os.path.join('invoices', file_name)
            pdf.output(file_path)
            
            folder_name = f"Student_{student_name}"
            folder_id = self.get_or_create_folder(service, folder_name)
            file_metadata = {'name': file_name, 'parents': [folder_id]}
            media = MediaFileUpload(file_path, mimetype='application/pdf')
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            
            service.permissions().create(fileId=file['id'], body={'type': 'anyone', 'role': 'reader'}).execute()
            uploaded = True
        
        if uploaded:
            messagebox.showinfo("Success", "Invoices uploaded to Google Drive")
        else:
            messagebox.showwarning("Warning", "No invoices selected to upload")
    
    def generate_pdf(self, invoice_id):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="DoReMi Music School", ln=True, align='C')
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="302 Satellite Blvd NE, Ste#C225, Suwanee, GA 30024", ln=True, align='C')
        pdf.cell(200, 10, txt="404-917-3348 | www.doremimusic.net", ln=True, align='C')
        pdf.ln(10)
        
        cursor.execute("SELECT s.name, i.month, i.year FROM invoices i JOIN students s ON i.student_id = s.id WHERE i.id=?", (invoice_id,))
        invoice = cursor.fetchone()
        pdf.cell(200, 10, txt=f"INVOICE for {invoice[0]}", ln=True, align='C')
        pdf.cell(200, 10, txt=f"Month: {invoice[1]}, Year: {invoice[2]}", ln=True, align='L')
        pdf.ln(10)
        
        cursor.execute("SELECT date, quantity, rate, amount, description FROM invoice_items WHERE invoice_id=?", (invoice_id,))
        items = cursor.fetchall()
        pdf.cell(50, 10, txt="Date", border=1)
        pdf.cell(30, 10, txt="Quantity", border=1)
        pdf.cell(30, 10, txt="Rate", border=1)
        pdf.cell(30, 10, txt="Amount", border=1)
        pdf.cell(40, 10, txt="Description", border=1)
        pdf.ln()
        
        total_amount = 0
        for item in items:
            pdf.cell(50, 10, txt=item[0], border=1)
            pdf.cell(30, 10, txt=str(item[1]), border=1)
            pdf.cell(30, 10, txt=str(item[2]), border=1)
            pdf.cell(30, 10, txt=str(item[3]), border=1)
            pdf.cell(40, 10, txt=item[4], border=1)
            pdf.ln()
            total_amount += item[3]
        
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Total: ${total_amount:.2f}", ln=True, align='R')
        return pdf
    
    def get_or_create_folder(self, service, folder_name):
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        response = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        folders = response.get('files', [])
        
        if folders:
            return folders[0]['id']
        else:
            folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            return folder['id']
    
    def send_sms(self):
        if not messagebox.askyesno("Confirm", "Send SMS for all invoices?"):
            return
        
        textbelt_key = os.getenv('TEXTBELT_KEY')
        if not textbelt_key:
            messagebox.showerror("Error", "Textbelt API key not found")
            return
        
        creds = load_credentials()
        if not creds:
            messagebox.showerror("Error", "Google Drive authentication required for links")
            return
        service = build('drive', 'v3', credentials=creds)
        
        sent = False
        for invoice in self.invoices_tree.get_children():
            invoice_id = self.invoices_tree.item(invoice)['values'][0]
            student_name = self.invoices_tree.item(invoice)['values'][1]
            cursor.execute("SELECT phone FROM students WHERE name=?", (student_name,))
            result = cursor.fetchone()
            if result:
                phone = result[0]
                
                # Generate and upload PDF to get the correct link
                pdf = self.generate_pdf(invoice_id)
                file_name = f"invoice_{student_name}_{self.invoices_tree.item(invoice)['values'][2]}_{self.invoices_tree.item(invoice)['values'][3]}.pdf"
                file_path = os.path.join('invoices', file_name)
                pdf.output(file_path)
                
                folder_name = f"Student_{student_name}"
                folder_id = self.get_or_create_folder(service, folder_name)
                file_metadata = {'name': file_name, 'parents': [folder_id]}
                media = MediaFileUpload(file_path, mimetype='application/pdf')
                file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                service.permissions().create(fileId=file['id'], body={'type': 'anyone', 'role': 'reader'}).execute()
                link = f"https://drive.google.com/file/d/{file['id']}/view?usp=sharing"
                
                message = f"Invoice for {student_name}: {link}"
                resp = requests.post('https://textbelt.com/text', {
                    'phone': phone,
                    'message': message,
                    'key': textbelt_key
                })
                result = resp.json()
                if result['success']:
                    sent = True
                else:
                    messagebox.showwarning("Warning", f"Failed to send SMS to {phone}: {result.get('error', 'Unknown error')}")
        
        if sent:
            messagebox.showinfo("Success", "SMS sent successfully")
        else:
            messagebox.showwarning("Warning", "No SMS sent; no invoices selected or no phone numbers found")

def on_closing():
    conn.close()
    root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = StudentApp(root)
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()