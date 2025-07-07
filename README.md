# DoReMi Music School Automation Project

## Overview
This project automates invoicing and student management for DoReMi Music School, where I work part-time as a piano instructor. The initial goal was to replace the manual 3-4 hour process of screenshotting and texting invoices with an automated system. The project has evolved into a Python-based app using Tkinter for a GUI, SQLite for data storage, and `fpdf` for PDF invoice generation, with plans for SMS and email integration.

## Project Checkpoint Updates

### Checkpoint 3 - Week 8 (July 06, 2025)
**Progress Update:**  
As of Checkpoint 3, the project has successfully transitioned from an Excel-based approach to a custom Python application. Key achievements include:
- Developed a student management interface to add students with details like name, lesson day, and contact information.
- Implemented PDF invoice generation, creating files named by student ID (e.g., `invoice_1_7_2025.pdf`) based on monthly lesson counts (e.g., 4 or 5 Saturdays).
- Stored student data in an SQLite database (`students.db`) for persistence.

**Next Steps:**  
- Integrate SMS and email functionality to distribute PDF invoices automatically.
- (Optional) Develop a lightweight schedule viewer for staff.

**Supporting Evidence:**  
- [Student Management Script](student_management.py)  
- [Sample Invoices](invoices/)  
- [Database File](students.db) (viewable with SQLite tools like DB Browser for SQLite)

## How to Use `student_management.py`
- Run student_management.py using any IDE
- Use the "Add Student" button to add students to the database. Once added, a "students.db" file will be created. This file can be viewed using a simple viewer such as DB Browser.
- Additional students added will edit the "students.db" database
- Use the "Generate Invoice" button to generate invoices for all students, and they will be placed in an "invoices" folder.

### Prerequisites
- Required libraries: `tkinter` (included with Python), `sqlite3` (included with Python), and `fpdf`.
