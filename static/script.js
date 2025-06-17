// script.js

function askQuestion() {
    const question = document.getElementById("question").value;

    if (!question) {
        alert("กรุณาพิมพ์คำถามก่อน");
        return;
    }

    // ส่งคำถามไปยัง Flask API
    fetch("/ask", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ question: question })
    })
    .then(response => response.json())
    .then(data => {
        // ตรวจสอบว่ามีคำตอบหรือไม่
        if (data.answer) {
            document.getElementById("answer").innerText = data.answer;
        } else {
            document.getElementById("answer").innerText = "ไม่พบคำตอบ";
        }
    })
    .catch(error => {
        console.error("Error:", error);
        document.getElementById("answer").innerText = "เกิดข้อผิดพลาดในการเชื่อมต่อกับ API";
    });
}
