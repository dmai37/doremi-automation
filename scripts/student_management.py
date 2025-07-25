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

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Database setup
conn = sqlite3.connect('students.db')
cursor = conn.cursor()

# Ensure family_id column exists
cursor.execute('PRAGMA table_info(students)')
columns = [col[1] for col in cursor.fetchall()]
if 'family_id' not in columns:
    cursor.execute('ALTER TABLE students ADD COLUMN family_id INTEGER')

# Create tables
cursor.execute('''CREATE TABLE IF NOT EXISTS families
                (family_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 family_name TEXT,
                 phone TEXT,
                 email TEXT)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS students
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 family_id INTEGER,
                 name TEXT,
                 deposit REAL,
                 signup_date TEXT,
                 dob TEXT,
                 parent_name TEXT,
                 phone TEXT,
                 email TEXT,
                 lesson_day TEXT,
                 teacher TEXT,
                 FOREIGN KEY(family_id) REFERENCES families(family_id))''')

cursor.execute('''CREATE TABLE IF NOT EXISTS invoices
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 family_id INTEGER,
                 month INTEGER,
                 year INTEGER,
                 FOREIGN KEY(family_id) REFERENCES families(family_id))''')

cursor.execute('''CREATE TABLE IF NOT EXISTS invoice_items
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 invoice_id INTEGER,
                 student_id INTEGER,
                 date TEXT,
                 quantity INTEGER,
                 rate REAL,
                 amount REAL,
                 description TEXT,
                 FOREIGN KEY(invoice_id) REFERENCES invoices(id),
                 FOREIGN KEY(student_id) REFERENCES students(id))''')

conn.commit()

# Google Drive authentication
def authenticate_google_drive():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    return creds

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
        
        # Fetch family_id and students
        cursor.execute("SELECT family_id FROM invoices WHERE id=?", (self.invoice_id,))
        self.family_id = cursor.fetchone()[0]
        cursor.execute("SELECT id, name FROM students WHERE family_id=?", (self.family_id,))
        self.students = cursor.fetchall()
        self.student_names = [student[1] for student in self.students]
        self.student_id_map = {name: id for id, name in self.students}
        
        # Treeview with Student column
        self.tree = ttk.Treeview(self, columns=("Student", "Date", "Quantity", "Rate", "Amount", "Description"), show="headings")
        self.tree.heading("Student", text="Student")
        self.tree.heading("Date", text="Date")
        self.tree.heading("Quantity", text="Quantity")
        self.tree.heading("Rate", text="Rate")
        self.tree.heading("Amount", text="Amount")
        self.tree.heading("Description", text="Description")
        self.tree.pack(fill="both", expand=True)
        
        # Fetch items with student name
        cursor.execute("""
            SELECT s.name, ii.date, ii.quantity, ii.rate, ii.amount, ii.description
            FROM invoice_items ii

            JOIN students s ON ii.student_id = s.id
            WHERE ii.invoice_id=?
        """, (self.invoice_id,))
        self.items = cursor.fetchall()
        for item in self.items:
            self.tree.insert("", "end", values=item)
        
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Add Item", command=self.add_item).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Edit Item", command=self.edit_item).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Delete Item", command=self.delete_item).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="Save Invoice", command=self.save_invoice).grid(row=0, column=3, padx=5)
    
    def add_item(self):
        if not self.student_names:
            messagebox.showerror("Error", "No students in this family")
            return
        student_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(self.student_names)])
        student_choice = simpledialog.askstring("Add Item", f"Select student:\n{student_list}\nEnter number:")
        try:
            student_index = int(student_choice) - 1
            if student_index < 0 or student_index >= len(self.student_names):
                raise ValueError
            student_name = self.student_names[student_index]
        except (ValueError, TypeError):
            messagebox.showerror("Error", "Invalid student selection")
            return
        date = simpledialog.askstring("Add Item", "Date (YYYY-MM-DD):")
        quantity = simpledialog.askinteger("Add Item", "Quantity:")
        rate = simpledialog.askfloat("Add Item", "Rate:")
        amount = quantity * rate if quantity and rate else 0
        description = simpledialog.askstring("Add Item", "Description:")
        if date and quantity and rate:
            self.tree.insert("", "end", values=(student_name, date, quantity, rate, amount, description))
    
    def edit_item(self):
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected)
        values = item['values']
        if not self.student_names:
            messagebox.showerror("Error", "No students in this family")
            return
        student_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(self.student_names)])
        student_choice = simpledialog.askstring("Edit Item", f"Select student:\n{student_list}\nEnter number:", initialvalue=str(self.student_names.index(values[0]) + 1) if values[0] in self.student_names else "")
        try:
            student_index = int(student_choice) - 1
            if student_index < 0 or student_index >= len(self.student_names):
                raise ValueError
            student_name = self.student_names[student_index]
        except (ValueError, TypeError):
            messagebox.showerror("Error", "Invalid student selection")
            return
        date = simpledialog.askstring("Edit Item", "Date (YYYY-MM-DD):", initialvalue=values[1])
        quantity = simpledialog.askinteger("Edit Item", "Quantity:", initialvalue=values[2])
        rate = simpledialog.askfloat("Edit Item", "Rate:", initialvalue=values[3])
        amount = quantity * rate if quantity and rate else 0
        description = simpledialog.askstring("Edit Item", "Description:", initialvalue=values[5])
        if date and quantity and rate:
            self.tree.item(selected, values=(student_name, date, quantity, rate, amount, description))
    
    def delete_item(self):
        selected = self.tree.selection()
        if selected:
            self.tree.delete(selected)
    
    def save_invoice(self):
        cursor.execute("DELETE FROM invoice_items WHERE invoice_id=?", (self.invoice_id,))
        for child in self.tree.get_children():
            values = self.tree.item(child)['values']
            student_name = values[0]
            student_id = self.student_id_map[student_name]
            cursor.execute('''INSERT INTO invoice_items 
                              (invoice_id, student_id, date, quantity, rate, amount, description) 
                              VALUES (?, ?, ?, ?, ?, ?, ?)''',
                           (self.invoice_id, student_id, values[1], values[2], values[3], values[4], values[5]))
        conn.commit()
        messagebox.showinfo("Success", "Invoice updated successfully")
        self.destroy()

class AddStudentWindow(tk.Toplevel):
    def __init__(self, parent, student=None):
        super().__init__(parent)
        self.title("Add Student" if student is None else "Edit Student")
        self.student = student
        self.num_students = tk.IntVar(value=1)
        
        self.num_students_label = tk.Label(self, text="Number of Students:")
        self.num_students_entry = tk.Entry(self, textvariable=self.num_students)
        self.num_students_label.grid(row=0, column=0, padx=5, pady=5)
        self.num_students_entry.grid(row=0, column=1, padx=5, pady=5)
        self.num_students_entry.bind("<Return>", self.update_student_fields)
        
        self.student_fields_frame = tk.Frame(self)
        self.student_fields_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        tk.Button(self, text="Save", command=self.save_student).grid(row=2, column=0, padx=5, pady=10)
        tk.Button(self, text="Cancel", command=self.destroy).grid(row=2, column=1, padx=5, pady=10)
        
        self.student_entries = []
        self.update_student_fields()
        
        if student:
            self.num_students.set(1)
            self.num_students_entry.config(state='disabled')
            fields = ["Student Name:", "Deposit Amount:", "Sign-up Date (YYYY-MM-DD):", 
                      "Date of Birth (YYYY-MM-DD):", "Parent Name:", "Phone Number:", 
                      "Email:", "Day of Week Taking Lessons", "Teacher:"]
            for i, field in enumerate(fields):
                self.student_entries[0][field].insert(0, student[i + 2])

    def update_student_fields(self, event=None):
        for widget in self.student_fields_frame.winfo_children():
            widget.destroy()
        self.student_entries = []
        num = self.num_students.get()
        for i in range(num):
            frame = tk.LabelFrame(self.student_fields_frame, text=f"Student {i+1}")
            frame.pack(fill="x", padx=5, pady=5)
            entries = {}
            fields = ["Student Name:", "Deposit Amount:", "Sign-up Date (YYYY-MM-DD):", 
                      "Date of Birth (YYYY-MM-DD):", "Parent Name:", "Phone Number:", 
                      "Email:", "Day of Week Taking Lessons", "Teacher:"]
            for j, field in enumerate(fields):
                tk.Label(frame, text=field).grid(row=j, column=0, padx=5, pady=5)
                entry = tk.Entry(frame)
                entry.grid(row=j, column=1, padx=5, pady=5)
                entries[field] = entry
            self.student_entries.append(entries)

    def save_student(self):
        if self.student:
            family_id = self.student[1]
            entries = self.student_entries[0]
            data = {field: entry.get() for field, entry in entries.items()}
            if not all(data[field] for field in data):
                messagebox.showerror("Error", "All fields must be filled")
                return
            cursor.execute('''UPDATE students SET 
                              family_id=?, name=?, deposit=?, signup_date=?, dob=?, parent_name=?, phone=?, email=?, lesson_day=?, teacher=?
                              WHERE id=?''',
                           (family_id, data["Student Name:"], 
                            float(data["Deposit Amount:"]) if data["Deposit Amount:"] else 0.0,
                            data["Sign-up Date (YYYY-MM-DD):"], 
                            data["Date of Birth (YYYY-MM-DD):"],
                            data["Parent Name:"], data["Phone Number:"], data["Email:"],
                            data["Day of Week Taking Lessons"], data["Teacher:"], 
                            self.student[0]))
        else:
            first_student_data = self.student_entries[0]
            phone = first_student_data["Phone Number:"].get()
            email = first_student_data["Email:"].get()
            if not phone or not email:
                messagebox.showerror("Error", "Phone and email required for family contact")
                return
            family_name = f"{first_student_data['Student Name:'].get()}'s Family"
            cursor.execute('''INSERT INTO families (family_name, phone, email) 
                              VALUES (?, ?, ?)''', (family_name, phone, email))
            family_id = cursor.lastrowid
            
            for entries in self.student_entries:
                data = {field: entry.get() for field, entry in entries.items()}
                if not all(data[field] for field in data):
                    messagebox.showerror("Error", "All fields must be filled")
                    return
                cursor.execute('''INSERT INTO students 
                                  (family_id, name, deposit, signup_date, dob, parent_name, phone, email, lesson_day, teacher) 
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                               (family_id, data["Student Name:"], 
                                float(data["Deposit Amount:"]) if data["Deposit Amount:"] else 0.0,
                                data["Sign-up Date (YYYY-MM-DD):"], 
                                data["Date of Birth (YYYY-MM-DD):"],
                                data["Parent Name:"], data["Phone Number:"], data["Email:"],
                                data["Day of Week Taking Lessons"], data["Teacher:"]))
        conn.commit()
        messagebox.showinfo("Success", "Student(s) added/updated successfully")
        self.destroy()

class StudentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DoReMi Student Management")
        
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)
        
        self.students_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.students_tab, text="Students")
        
        self.invoices_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.invoices_tab, text="Invoices")
        
        self.setup_students_tab()
        self.setup_invoices_tab()

    def setup_students_tab(self):
        search_frame = ttk.Frame(self.students_tab)
        search_frame.pack(pady=5)
        self.student_search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.student_search_var, width=30).pack(side="left", padx=5)
        ttk.Button(search_frame, text="Search", command=self.search_students).pack(side="left")
        ttk.Button(search_frame, text="Clear", command=self.clear_student_search).pack(side="left")

        self.students_tree = ttk.Treeview(self.students_tab, columns=("ID", "Name", "Lesson Day"), show="headings")
        self.students_tree.heading("ID", text="ID")
        self.students_tree.heading("Name", text="Name")
        self.students_tree.heading("Lesson Day", text="Lesson Day")
        self.students_tree.pack(fill="both", expand=True)
        
        button_frame = ttk.Frame(self.students_tab)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Add Student", command=self.add_student).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Edit Student", command=self.edit_student).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Delete Student", command=self.delete_student).grid(row=0, column=2, padx=5)
        
        self.load_students()

    def load_students(self, search_term=None):
        for item in self.students_tree.get_children():
            self.students_tree.delete(item)
        query = "SELECT id, name, lesson_day FROM students"
        if search_term:
            query += " WHERE name LIKE ?"
            cursor.execute(query, (f"%{search_term}%",))
        else:
            cursor.execute(query)
        for student in cursor.fetchall():
            self.students_tree.insert("", "end", values=student)

    def search_students(self):
        self.load_students(self.student_search_var.get())

    def clear_student_search(self):
        self.student_search_var.set("")
        self.load_students()

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
        search_frame = ttk.Frame(self.invoices_tab)
        search_frame.pack(pady=5)
        self.invoice_search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.invoice_search_var, width=30).pack(side="left", padx=5)
        ttk.Button(search_frame, text="Search", command=self.search_invoices).pack(side="left")
        ttk.Button(search_frame, text="Clear", command=self.clear_invoice_search).pack(side="left")

        self.invoices_tree = ttk.Treeview(self.invoices_tab, columns=("ID", "Students", "Month", "Year"), show="headings")
        self.invoices_tree.heading("ID", text="ID")
        self.invoices_tree.heading("Students", text="Students")
        self.invoices_tree.heading("Month", text="Month")
        self.invoices_tree.heading("Year", text="Year")
        self.invoices_tree.pack(fill="both", expand=True)
        
        button_frame = ttk.Frame(self.invoices_tab)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Generate Invoices", command=self.generate_invoices).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Edit Invoice", command=self.edit_invoice).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Upload to Google Drive", command=self.upload_invoices).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="Send SMS", command=self.send_sms).grid(row=0, column=3, padx=5)
        ttk.Button(button_frame, text="Delete Invoice", command=self.delete_invoice).grid(row=0, column=4, padx=5)
        
        self.load_invoices()

    def load_invoices(self, search_term=None):
        for item in self.invoices_tree.get_children():
            self.invoices_tree.delete(item)
        query = """
            SELECT i.id, GROUP_CONCAT(s.name, ', '), i.month, i.year
            FROM invoices i
            JOIN students s ON s.family_id = i.family_id
        """
        if search_term:
            query += " WHERE s.name LIKE ?"
            cursor.execute(query + " GROUP BY i.id, i.month, i.year", (f"%{search_term}%",))
        else:
            cursor.execute(query + " GROUP BY i.id, i.month, i.year")
        for invoice in cursor.fetchall():
            students = invoice[1].split(', ')
            students.sort()
            self.invoices_tree.insert("", "end", values=(invoice[0], ', '.join(students), invoice[2], invoice[3]))

    def search_invoices(self):
        self.load_invoices(self.invoice_search_var.get())

    def clear_invoice_search(self):
        self.invoice_search_var.set("")
        self.load_invoices()

    def generate_invoices(self):
        if not messagebox.askyesno("Confirm", "Generate invoices for the current month?"):
            return
        current_date = datetime.date.today()
        current_year = current_date.year
        current_month = current_date.month
        
        cursor.execute("SELECT DISTINCT family_id FROM students WHERE family_id IS NOT NULL")
        family_ids = cursor.fetchall()
        
        for family_id_tuple in family_ids:
            family_id = family_id_tuple[0]
            cursor.execute("SELECT id FROM invoices WHERE family_id=? AND month=? AND year=?", 
                           (family_id, current_month, current_year))
            if cursor.fetchone():
                continue
            
            invoice_id = self.create_invoice(family_id, current_month, current_year)
            cursor.execute("SELECT id, lesson_day FROM students WHERE family_id=?", (family_id,))
            students = cursor.fetchall()
            
            for student in students:
                student_id, lesson_day = student
                if lesson_day:
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
                                          (invoice_id, student_id, date, quantity, rate, amount, description) 
                                          VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                       (invoice_id, student_id, date.strftime('%Y-%m-%d'), 1, 30, 30, "Lesson"))
        conn.commit()
        self.load_invoices()
        messagebox.showinfo("Success", "Invoices generated successfully")

    def create_invoice(self, family_id, month, year):
        cursor.execute("INSERT INTO invoices (family_id, month, year) VALUES (?, ?, ?)", 
                       (family_id, month, year))
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
        
        creds = load_credentials() or authenticate_google_drive()
        if not creds:
            messagebox.showerror("Error", "Google Drive authentication failed")
            return
        
        service = build('drive', 'v3', credentials=creds)
        os.makedirs('invoices', exist_ok=True)
        
        for invoice in self.invoices_tree.get_children():
            invoice_id = self.invoices_tree.item(invoice)['values'][0]
            family_id = self.get_family_id(invoice_id)
            month = self.invoices_tree.item(invoice)['values'][2]
            year = self.invoices_tree.item(invoice)['values'][3]
            
            pdf = self.generate_pdf(invoice_id)
            file_name = f"invoice_family_{family_id}_{month}_{year}.pdf"
            file_path = os.path.join('invoices', file_name)
            pdf.output(file_path)
            
            folder_name = f"Family_{family_id}"
            folder_id = self.get_or_create_folder(service, folder_name)
            file_metadata = {'name': file_name, 'parents': [folder_id]}
            media = MediaFileUpload(file_path, mimetype='application/pdf')
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            service.permissions().create(fileId=file['id'], body={'type': 'anyone', 'role': 'reader'}).execute()
        
        messagebox.showinfo("Success", "Invoices uploaded to Google Drive")

    def get_family_id(self, invoice_id):
        cursor.execute("SELECT family_id FROM invoices WHERE id=?", (invoice_id,))
        return cursor.fetchone()[0]

    def generate_pdf(self, invoice_id):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="DoReMi Music School", ln=True, align='C')
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="302 Satellite Blvd NE, Ste#C225, Suwanee, GA 30024", ln=True, align='C')
        pdf.cell(200, 10, txt="404-917-3348 | www.doremimusic.net", ln=True, align='C')
        pdf.ln(10)
        
        cursor.execute("SELECT family_id, month, year FROM invoices WHERE id=?", (invoice_id,))
        invoice = cursor.fetchone()
        family_id = invoice[0]
        
        cursor.execute("SELECT name FROM students WHERE family_id=?", (family_id,))
        students = [row[0] for row in cursor.fetchall()]
        students.sort()
        pdf.cell(200, 10, txt=f"INVOICE for {', '.join(students)}", ln=True, align='C')
        pdf.cell(200, 10, txt=f"Month: {invoice[1]}, Year: {invoice[2]}", ln=True, align='L')
        pdf.ln(10)
        
        cursor.execute("SELECT s.name, ii.date, ii.quantity, ii.rate, ii.amount, ii.description FROM invoice_items ii JOIN students s ON ii.student_id = s.id WHERE ii.invoice_id=?", (invoice_id,))
        items = cursor.fetchall()
        pdf.cell(40, 10, txt="Student", border=1)
        pdf.cell(30, 10, txt="Date", border=1)
        pdf.cell(20, 10, txt="Qty", border=1)
        pdf.cell(30, 10, txt="Rate", border=1)
        pdf.cell(30, 10, txt="Amount", border=1)
        pdf.cell(40, 10, txt="Description", border=1)
        pdf.ln()
        
        total_amount = 0
        for item in items:
            pdf.cell(40, 10, txt=item[0], border=1)
            pdf.cell(30, 10, txt=item[1], border=1)
            pdf.cell(20, 10, txt=str(item[2]), border=1)
            pdf.cell(30, 10, txt=f"${item[3]:.2f}", border=1)
            pdf.cell(30, 10, txt=f"${item[4]:.2f}", border=1)
            pdf.cell(40, 10, txt=item[5], border=1)
            pdf.ln()
            total_amount += item[4]
        
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Total: ${total_amount:.2f}", ln=True, align='R')
        return pdf

    def get_or_create_folder(self, service, folder_name):
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        response = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        folders = response.get('files', [])
        return folders[0]['id'] if folders else service.files().create(body={'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}, fields='id').execute()['id']

    def send_sms(self):
        if not messagebox.askyesno("Confirm", "Send SMS for all invoices?"):
            return
        
        textbelt_key = os.getenv('TEXTBELT_KEY')
        if not textbelt_key:
            messagebox.showerror("Error", "Textbelt API key not found")
            return
        
        creds = load_credentials() or authenticate_google_drive()
        if not creds:
            messagebox.showerror("Error", "Google Drive authentication required")
            return
        service = build('drive', 'v3', credentials=creds)
        
        for invoice in self.invoices_tree.get_children():
            invoice_id = self.invoices_tree.item(invoice)['values'][0]
            family_id = self.get_family_id(invoice_id)
            cursor.execute("SELECT phone FROM families WHERE family_id=?", (family_id,))
            phone = cursor.fetchone()[0]
            
            pdf = self.generate_pdf(invoice_id)
            file_name = f"invoice_family_{family_id}_{self.invoices_tree.item(invoice)['values'][2]}_{self.invoices_tree.item(invoice)['values'][3]}.pdf"
            file_path = os.path.join('invoices', file_name)
            pdf.output(file_path)
            
            folder_id = self.get_or_create_folder(service, f"Family_{family_id}")
            file_metadata = {'name': file_name, 'parents': [folder_id]}
            media = MediaFileUpload(file_path, mimetype='application/pdf')
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            service.permissions().create(fileId=file['id'], body={'type': 'anyone', 'role': 'reader'}).execute()
            link = f"https://drive.google.com/file/d/{file['id']}/view?usp=sharing"
            
            message = f"Invoice for Family ID {family_id}: {link}"
            resp = requests.post('https://textbelt.com/text', {'phone': phone, 'message': message, 'key': textbelt_key})
            if not resp.json()['success']:
                messagebox.showwarning("Warning", f"Failed to send SMS to {phone}")
        
        messagebox.showinfo("Success", "SMS sent successfully")

    def delete_invoice(self):
        selected = self.invoices_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an invoice to delete")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete the selected invoice?"):
            invoice_id = self.invoices_tree.item(selected)['values'][0]
            cursor.execute("DELETE FROM invoice_items WHERE invoice_id=?", (invoice_id,))
            cursor.execute("DELETE FROM invoices WHERE id=?", (invoice_id,))
            conn.commit()
            self.load_invoices()
            messagebox.showinfo("Success", "Invoice deleted successfully")

def on_closing():
    conn.close()
    root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = StudentApp(root)
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()