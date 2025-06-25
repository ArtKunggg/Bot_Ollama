from flask import Flask, request, jsonify, render_template
import mysql.connector
import ollama

app = Flask(__name__)

# 🔧 เชื่อมต่อ MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="Bot"
)

# 🔁 ตรวจสอบการเชื่อมต่อ
def get_db():
    global db
    if not db.is_connected():
        db.reconnect()
    return db

# ✅ ค้นชื่อจากคำถาม
def extract_name_from_question(question):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT first_name FROM name")
    names = [row[0].lower() for row in cursor.fetchall()]
    cursor.close()

    for name in names:
        if name in question.lower():
            return name
    return None

# ✅ ค้นบุคคลจากชื่อ
def search_name(keyword):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM name WHERE first_name LIKE %s OR last_name LIKE %s",
                   (f"%{keyword}%", f"%{keyword}%"))
    result = cursor.fetchall()
    cursor.close()
    return result

# ✅ ดึงข้อมูลแผนกทั้งหมด
def get_department_info():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM department")
    result = cursor.fetchall()
    cursor.close()
    return result

# ✅ จำคำถามที่เคยตอบ
def search_memory(question):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT answer FROM qa_memory WHERE question = %s", (question,))
    result = cursor.fetchone()
    cursor.close()
    return result['answer'] if result else None

def save_to_memory(question, answer):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO qa_memory (question, answer) VALUES (%s, %s)", (question, answer))
    conn.commit()
    cursor.close()

# ✅ ถาม Ollama
def ask_ollama(question, context):
    prompt = f"""
คุณคือแชทบอทอัจฉริยะที่พูดจาเป็นกันเอง ตอบคำถามด้วยความสุภาพและเข้าใจง่าย
งานของคุณคือช่วยผู้ใช้งานตอบคำถามจากข้อมูลที่ให้ไว้ด้านล่างเท่านั้น

📦 ข้อมูล:
{context}

❓ คำถามจากผู้ใช้:
{question}

📌 คำแนะนำในการตอบ:
- ถ้าพบข้อมูลที่เกี่ยวข้อง ให้สรุปคำตอบอย่างเป็นธรรมชาติ
- ถ้าไม่พบข้อมูลที่ตรงกับคำถาม ให้ตอบว่า "ขออภัยค่ะ ไม่พบข้อมูลในระบบ"
- ใช้ภาษาไทยแบบเป็นกันเอง ไม่เป็นทางการเกินไป

🧠 กรุณาตอบเฉพาะจากข้อมูลข้างต้นเท่านั้น:
"""

    response = ollama.chat(
        model="llama3:8b",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['message']['content']


# ✅ เส้นทางถาม/ตอบ
@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    question = data.get("question", "").strip().lower()

    # ✅ 1. ลองเช็คใน memory ก่อน
    cached_answer = search_memory(question)
    if cached_answer:
        return jsonify({"answer": cached_answer})

    conn = get_db()
    cursor = conn.cursor()

    # ✅ 2. ตรวจสอบคำถามเชิงสถิติ
    if "มีกี่คน" in question or "จำนวนคน" in question:
        cursor.execute("SELECT COUNT(*) FROM name")
        count = cursor.fetchone()[0]
        return jsonify({"answer": f"มีทั้งหมด {count} คนค่ะ"})

    if "มีกี่อีเมล" in question or "จำนวนอีเมล" in question:
        cursor.execute("SELECT COUNT(DISTINCT email) FROM name")
        count = cursor.fetchone()[0]
        return jsonify({"answer": f"มีทั้งหมด {count} อีเมลค่ะ"})

    if "ผู้หญิง" in question:
        cursor.execute("SELECT COUNT(*) FROM name WHERE gender = 'Female'")
        count = cursor.fetchone()[0]
        return jsonify({"answer": f"มีผู้หญิงทั้งหมด {count} คนค่ะ"})

    if "ผู้ชาย" in question:
        cursor.execute("SELECT COUNT(*) FROM name WHERE gender = 'Male'")
        count = cursor.fetchone()[0]
        return jsonify({"answer": f"มีผู้ชายทั้งหมด {count} คนค่ะ"})

    cursor.close()

    # ✅ 3. ตรวจสอบคำถามเกี่ยวกับแผนก
    if "แผนก" in question or "บริษัท" in question:
        departments = get_department_info()
        context = "\n".join([f"{d['department']} - บริษัท {d['company']}" for d in departments])
        answer = ask_ollama(question, context)
        save_to_memory(question, answer)
        return jsonify({"answer": answer})

    # ✅ 4. ถามเกี่ยวกับบุคคล
    keyword = extract_name_from_question(question)
    if not keyword:
        return jsonify({"answer": "ไม่พบชื่อบุคคลในคำถามค่ะ"}), 404

    people = search_name(keyword)
    if not people:
        return jsonify({"answer": "ไม่พบข้อมูลบุคคลในฐานข้อมูลค่ะ"}), 404

    context = "\n".join([
        f"{p['first_name']} {p['last_name']} - {p['email']} ({p['gender']})"
        for p in people
    ])

    answer = ask_ollama(question, context)
    save_to_memory(question, answer)
    return jsonify({"answer": answer})


# ✅ หน้าเว็บหลัก
@app.route("/")
def index():
    return render_template("index.html")

# ✅ เริ่มรัน
if __name__ == "__main__":
    app.run(debug=True)
