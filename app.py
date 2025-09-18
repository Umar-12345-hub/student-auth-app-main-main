from flask import Flask, render_template, request, redirect, url_for, session
import json, os, qrcode, base64
from io import BytesIO
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super_secret_key"

# ---------------- FILE PATHS ----------------
LECTURERS_FILE = "lecturers.json"
STUDENTS_FILE = "students.json"
SECTIONS_FILE = "sections.json"

# ---------------- HELPERS ----------------
def load_data(file):
    if not os.path.exists(file):
        return []
    with open(file, "r") as f:
        return json.load(f)

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- LECTURER AUTH ----------------
@app.route("/lecturer/register", methods=["GET", "POST"])
def lecturer_register():
    if request.method == "POST":
        name = request.form["name"]
        password = request.form["password"]

        lecturers = load_data(LECTURERS_FILE)
        lecturers.append({"name": name, "password": password})
        save_data(LECTURERS_FILE, lecturers)

        return redirect(url_for("lecturer_login"))
    return render_template("lecturer_register.html")

@app.route("/lecturer/login", methods=["GET", "POST"])
def lecturer_login():
    if request.method == "POST":
        name = request.form["name"]
        password = request.form["password"]

        lecturers = load_data(LECTURERS_FILE)
        for lec in lecturers:
            if lec["name"] == name and lec["password"] == password:
                session["lecturer"] = name
                return redirect(url_for("lecturer_dashboard"))
        return render_template("lecturer_login.html", error="Invalid login")
    return render_template("lecturer_login.html")

@app.route("/lecturer/dashboard")
def lecturer_dashboard():
    if "lecturer" not in session:
        return redirect(url_for("lecturer_login"))
    sections = load_data(SECTIONS_FILE)
    return render_template("lecturer_dashboard.html", lecturer=session["lecturer"], sections=sections)

@app.route("/lecturer/logout")
def lecturer_logout():
    session.pop("lecturer", None)
    return redirect(url_for("lecturer_login"))

# ---------------- CREATE SECTION + QR ----------------
@app.route("/create_section", methods=["POST"])
def create_section():
    if "lecturer" not in session:
        return redirect(url_for("lecturer_login"))

    section_name = request.form["section_name"]
    sections = load_data(SECTIONS_FILE)
    section_id = str(len(sections) + 1)

    section = {
        "id": section_id,
        "name": section_name,
        "lecturer": session["lecturer"],
        "attendance": []
    }
    sections.append(section)
    save_data(SECTIONS_FILE, sections)

    # generate QR code with link
    url = url_for("student_mark_attendance", section_id=section_id, _external=True)
    qr = qrcode.make(url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render_template("section_created.html", section=section, qr_code=qr_base64)

# ---------------- STUDENT AUTH ----------------
@app.route("/student/register", methods=["GET", "POST"])
def student_register():
    if request.method == "POST":
        name = request.form["name"]
        password = request.form["password"]

        students = load_data(STUDENTS_FILE)
        students.append({"name": name, "password": password})
        save_data(STUDENTS_FILE, students)

        return redirect(url_for("student_login"))
    return render_template("student_register.html")

@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        name = request.form["name"]
        password = request.form["password"]

        students = load_data(STUDENTS_FILE)
        for stu in students:
            if stu["name"] == name and stu["password"] == password:
                session["student"] = name
                next_url = session.pop("next", None)
                return redirect(next_url or url_for("student_dashboard"))
        return render_template("student_login.html", error="Invalid login")
    return render_template("student_login.html")

@app.route("/student/dashboard")
def student_dashboard():
    if "student" not in session:
        return redirect(url_for("student_login"))
    sections = load_data(SECTIONS_FILE)
    return render_template("student_dashboard.html", student=session["student"], sections=sections)

@app.route("/student/logout")
def student_logout():
    session.pop("student", None)
    return redirect(url_for("student_login"))

# ---------------- ATTENDANCE ----------------
@app.route("/student/mark/<section_id>", methods=["GET", "POST"])
def student_mark_attendance(section_id):
    if "student" not in session:
        session["next"] = url_for("student_mark_attendance", section_id=section_id)
        return redirect(url_for("student_login"))

    student_name = session["student"]
    sections = load_data(SECTIONS_FILE)

    for section in sections:
        if section["id"] == section_id:
            if request.method == "POST":
                status = request.form["status"]
                section["attendance"].append({
                    "student": student_name,
                    "status": status,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                save_data(SECTIONS_FILE, sections)
                return render_template("attendance_success.html", section=section)
            return render_template("mark_attendance.html", section=section)

    return "Section not found"

@app.route("/lecturer/attendance/<section_id>")
def view_attendance(section_id):
    if "lecturer" not in session:
        return redirect(url_for("lecturer_login"))
    sections = load_data(SECTIONS_FILE)
    for section in sections:
        if section["id"] == section_id:
            return render_template("view_attendance.html", section=section)
    return "Section not found"

if __name__ == "__main__":
    app.run(debug=True)
