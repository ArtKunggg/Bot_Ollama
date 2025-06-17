from flask import Flask, request, jsonify
from flask import render_template
import mysql.connector
import ollama

app = Flask(__name__)

# 🔧 เชื่อมต่อฐานข้อมูล MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  # แก้ให้ตรงกับเครื่องคุณ
    database="Bot"
)

# 🔁 ตรวจสอบการเชื่อมต่อฐานข้อมูล
def get_db():
    global db
    if not db.is_connected():
        db.reconnect()
    return db

# 🔍 ค้นหาชื่อจากคำถาม
def search_name(keyword):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM name WHERE first_name LIKE %s OR last_name LIKE %s", (f"%{keyword}%", f"%{keyword}%"))
    result = cursor.fetchall()
    cursor.close()
    return result

# 🧠 ใช้ Ollama ตอบคำถาม
def ask_ollama(question, context):
    prompt = f"""คุณคือแชทบอทที่ช่วยตอบคำถามเกี่ยวกับข้อมูลของบุคคลโดยใช้ข้อมูลที่ให้มา
ข้อมูล:
{context}

คำถาม: {question}
ตอบเป็นภาษาไทย:
"""
    response = ollama.chat(
        model="llama3",  # หรือเปลี่ยนเป็นโมเดลอื่นที่คุณใช้
        messages=[{"role": "user", "content": prompt}]
    )
    return response['message']['content']

# 🌐 เส้นทางหลักในการถาม-ตอบ
@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    question = data.get("question", "").lower()

    conn = get_db()
    cursor = conn.cursor()

    # 📊 ตรวจสอบคำถามแนวนับจำนวน
    if "มีกี่คน" in question or "จำนวนคน" in question:
        cursor.execute("SELECT COUNT(*) FROM name")
        count = cursor.fetchone()[0]
        return jsonify({"answer": f"มีทั้งหมด {count} คนค่ะ"})

    if "มีกี่อีเมล" in question or "จำนวนอีเมล" in question:
        cursor.execute("SELECT COUNT(DISTINCT email) FROM name")
        count = cursor.fetchone()[0]
        return jsonify({"answer": f"มีทั้งหมด {count} อีเมลค่ะ"})

    if "ผู้หญิงกี่คน" in question:
        cursor.execute("SELECT COUNT(*) FROM name WHERE gender = 'Female'")
        count = cursor.fetchone()[0]
        return jsonify({"answer": f"มีผู้หญิงทั้งหมด {count} คนค่ะ"})

    if "ผู้ชายกี่คน" in question:
        cursor.execute("SELECT COUNT(*) FROM name WHERE gender = 'Male'")
        count = cursor.fetchone()[0]
        return jsonify({"answer": f"มีผู้ชายทั้งหมด {count} คนค่ะ"})

    cursor.close()

    # 🔄 คำถามทั่วไป ส่งต่อให้ Ollama ตอบ
    keyword = question.split()[0]
    people = search_name(keyword)

    if not people:
        return jsonify({"answer": "ไม่พบข้อมูลบุคคลในฐานข้อมูลค่ะ"}), 404

    context = "\n".join([
        f"{p['first_name']} {p['last_name']} - {p['email']} ({p['gender']})"
        for p in people
    ])

    answer = ask_ollama(question, context)
    return jsonify({"answer": answer})

@app.route("/")
def index():
    return render_template("index.html")

# 🚀 เริ่มรัน Flask
if __name__ == "__main__":
    app.run(debug=True)
