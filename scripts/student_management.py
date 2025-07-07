import tkinter as tk
from tkinter import messagebox
import sqlite3
import datetime
import os
from fpdf import FPDF

conn = sqlite3.connect('students.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS students
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT,
                 deposit REAL,
                 signup_date TEXT,
                 dob TEXT,
                 parent_name TEXT,
                 phone TEXT,
                 email TEXT,
                 lesson_day TEXT,  # Added lesson_day column
                 teacher TEXT)''')
conn.commit()

class AddStudentWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Add Student")
        
        # Define fields
        fields = [
            "Student Name:", "Deposit Amount:", "Sign-up Date (YYYY-MM-DD):", 
            "Date of Birth (YYYY-MM-DD):", "Parent Name:", "Phone Number:", 
            "Email:", "Day of Week Taking Lessons", "Teacher:"
        ]
        self.entries = {}
        
        for i, field in enumerate(fields):
            tk.Label(self, text=field).grid(row=i, column=0, padx=5, pady=5)
            entry = tk.Entry(self)
            entry.grid(row=i, column=1, padx=5, pady=5)
            self.entries[field] = entry
        
        save_button = tk.Button(self, text="Save", command=self.save_student)
        save_button.grid(row=len(fields), column=0, padx=5, pady=10)
        cancel_button = tk.Button(self, text="Cancel", command=self.destroy)
        cancel_button.grid(row=len(fields), column=1, padx=5, pady=10)
    
    def save_student(self):
        data = {field: entry.get() for field, entry in self.entries.items()}
        
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
            conn.commit()
            messagebox.showinfo("Success", "Student added successfully")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))

class StudentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Student Management")
        
        self.add_button = tk.Button(root, text="Add Student", command=self.add_student)
        self.add_button.pack(pady=20)
        
        self.generate_button = tk.Button(root, text="Generate Invoices", command=self.generate_invoices)
        self.generate_button.pack(pady=20)
    
    def add_student(self):
        AddStudentWindow(self.root)
    
    def generate_invoices(self):
        current_date = datetime.date.today()
        current_year = current_date.year
        current_month = current_date.month
        due_date = datetime.date(current_year, current_month, 16)
        
        cursor.execute("SELECT id, name, lesson_day FROM students")
        students = cursor.fetchall()
        
        if not os.path.exists('invoices'):
            os.makedirs('invoices')
        
        day_map = {
            "Monday": 0,
            "Tuesday": 1,
            "Wednesday": 2,
            "Thursday": 3,
            "Friday": 4,
            "Saturday": 5,
            "Sunday": 6
        }
        
        # Process each student
        for student in students:
            student_id, name, lesson_day = student
            if lesson_day and lesson_day in day_map:
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
                
                total_amount = len(dates) * 30
                
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                
                pdf.cell(200, 10, txt="Do Re Mi Music", ln=True, align='C')
                pdf.cell(200, 10, txt="302 Satellite Blvd NE, Ste#C225, Suwanee, GA 30024", ln=True, align='C')
                pdf.cell(200, 10, txt="404-917-3348", ln=True, align='C')
                pdf.cell(200, 10, txt="www.doremimusic.net", ln=True, align='C')
                pdf.ln(10)
                
                pdf.cell(200, 10, txt="INVOICE", ln=True, align='C')
                pdf.cell(200, 10, txt=f"Date: {current_date.strftime('%d-%b-%y')}", ln=True, align='L')
                pdf.cell(200, 10, txt=f"Due: {due_date.strftime('%d-%b-%y')}", ln=True, align='L')
                pdf.cell(200, 10, txt=f"Student: {name}", ln=True, align='L')
                pdf.ln(10)
                
                pdf.cell(50, 10, txt="Date", border=1)
                pdf.cell(30, 10, txt="Quantity", border=1)
                pdf.cell(30, 10, txt="Rate", border=1)
                pdf.cell(30, 10, txt="Amount", border=1)
                pdf.ln()
                
                for date in dates:
                    pdf.cell(50, 10, txt=date.strftime('%d-%b-%y'), border=1)
                    pdf.cell(30, 10, txt="1", border=1)
                    pdf.cell(30, 10, txt="30", border=1)
                    pdf.cell(30, 10, txt="30", border=1)
                    pdf.ln()
                
                pdf.ln(10)
                pdf.cell(200, 10, txt=f"Total: ${total_amount:.2f}", ln=True, align='R')
                
                file_name = f"invoice_{student_id}_{current_month}_{current_year}.pdf"
                file_path = os.path.join('invoices', file_name)
                pdf.output(file_path)
        
        messagebox.showinfo("Success", "Invoices generated successfully in the 'invoices' folder")

def on_closing():
    conn.close()
    root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = StudentApp(root)
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()