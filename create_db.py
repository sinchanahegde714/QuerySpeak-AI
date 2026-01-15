import sqlite3

# Create / connect to database
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# -------------------------------
# 1. Employees table
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    department TEXT,
    salary INTEGER,
    hire_date TEXT
)
""")

employees = [
    ("Aarav", "Engineering", 90000, "2021-02-12"),
    ("Diya", "Marketing", 70000, "2020-07-30"),
    ("Kabir", "Sales", 65000, "2022-01-15"),
    ("Neha", "Engineering", 120000, "2019-11-01"),
    ("Ravi", "Finance", 80000, "2023-03-01")
]

cursor.executemany(
    "INSERT INTO employees (name, department, salary, hire_date) VALUES (?, ?, ?, ?)",
    employees
)

# -------------------------------
# 2. Departments table
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    department_name TEXT,
    manager TEXT
)
""")

departments = [
    ("Engineering", "Neha"),
    ("Marketing", "Diya"),
    ("Sales", "Kabir"),
    ("Finance", "Ravi")
]

cursor.executemany(
    "INSERT INTO departments (department_name, manager) VALUES (?, ?)",
    departments
)

# -------------------------------
# 3. Projects table
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT,
    department_id INTEGER,
    start_date TEXT,
    end_date TEXT,
    FOREIGN KEY (department_id) REFERENCES departments(id)
)
""")

projects = [
    ("AI Chatbot", 1, "2023-01-01", "2023-06-01"),
    ("Brand Campaign", 2, "2022-03-15", "2022-08-30"),
    ("Market Expansion", 3, "2021-05-01", "2021-12-01"),
    ("Financial Dashboard", 4, "2024-01-01", "2024-07-01")
]

cursor.executemany(
    "INSERT INTO projects (project_name, department_id, start_date, end_date) VALUES (?, ?, ?, ?)",
    projects
)

# -------------------------------
# 4. Employee-Project Mapping
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS employee_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER,
    project_id INTEGER,
    role TEXT,
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
)
""")

employee_projects = [
    (1, 1, "Developer"),
    (4, 1, "Tech Lead"),
    (2, 2, "Coordinator"),
    (3, 3, "Sales Lead"),
    (5, 4, "Analyst"),
]

cursor.executemany(
    "INSERT INTO employee_projects (employee_id, project_id, role) VALUES (?, ?, ?)",
    employee_projects
)

conn.commit()
conn.close()

print("Expanded database created with departments, projects, and employee-project relations.")
