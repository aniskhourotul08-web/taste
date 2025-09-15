import os
import re
import subprocess
import datetime
import json
from flask import Flask, request, render_template_string

UPLOAD_FOLDER = "uploads"
HISTORY_FILE = "history.json"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# 📝 تحميل التاريخ من JSON عند بدء التشغيل
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        history = json.load(f)
else:
    history = []

# 🎨 HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Python Runner Pro</title>
    <style>
        body { font-family: "Segoe UI", sans-serif; margin: 0; background: #f0f2f5; }
        header { background: linear-gradient(90deg, #4f46e5, #9333ea); color: white; padding: 20px; text-align: center; }
        .container { max-width: 900px; margin: 30px auto; padding: 20px; }
        .card { background: white; border-radius: 16px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); padding: 20px; margin-bottom: 20px; }
        h1 { margin: 0; font-size: 28px; }
        h2 { margin-bottom: 10px; color: #333; }
        input[type=file] { margin: 15px 0; padding: 8px; }
        button { background: #4f46e5; color: white; padding: 10px 20px; border: none;
                 border-radius: 10px; cursor: pointer; font-weight: bold; transition: 0.3s; }
        button:hover { background: #4338ca; }
        pre { background: #111827; color: #10b981; padding: 15px; border-radius: 10px; overflow-x: auto; font-size: 14px; }
        .error { color: #ef4444; }
        .history-item { padding: 15px; border-left: 4px solid #4f46e5; margin-bottom: 15px; background: #fafafa; border-radius: 10px; }
        .timestamp { font-size: 12px; color: #6b7280; }
    </style>
</head>
<body>
    <header>
        <h1>🚀 Python Runner Pro</h1>
        <p>ارفع ملفات بايثون، يتم تثبيت المتطلبات وتشغيلها تلقائيًا مع حفظ التاريخ</p>
    </header>
    <div class="container">

        <!-- Form -->
        <div class="card">
            <h2>📂 Upload Python File</h2>
            <form method="POST" enctype="multipart/form-data">
                <input type="file" name="file" required>
                <br>
                <button type="submit">Upload & Run</button>
            </form>
        </div>

        <!-- History -->
        {% if history %}
        <div class="card">
            <h2>📝 History</h2>
            {% for item in history %}
            <div class="history-item">
                <strong>{{ item.filename }}</strong>
                <div class="timestamp">{{ item.time }}</div>
                <h4>✅ Output:</h4>
                <pre>{{ item.output }}</pre>
                {% if item.error %}
                <h4 class="error">⚠️ Errors:</h4>
                <pre class="error">{{ item.error }}</pre>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

# 🔎 استخراج المكتبات
def extract_imports(filepath):
    imports = set()
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            match = re.match(r'^\s*(?:import|from)\s+([a-zA-Z0-9_]+)', line)
            if match:
                lib = match.group(1)
                if lib not in ("os", "sys", "re", "subprocess", "flask", "json", "datetime"):
                    imports.add(lib)
    return imports

@app.route("/", methods=["GET", "POST"])
def upload_file():
    global history
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            return render_template_string(HTML_TEMPLATE, history=history)

        filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(filepath)

        # 📦 تحليل المكتبات وتثبيتها
        imports = extract_imports(filepath)
        with open("requirements.txt", "a") as f:
            for lib in imports:
                f.write(f"{lib}\n")
        try:
            subprocess.check_call([os.sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        except subprocess.CalledProcessError as e:
            entry = {
                "filename": file.filename,
                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "output": "",
                "error": f"pip install failed: {str(e)}"
            }
            history.insert(0, entry)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            return render_template_string(HTML_TEMPLATE, history=history)

        # ▶️ تشغيل الملف
        try:
            result = subprocess.run(
                [os.sys.executable, filepath],
                capture_output=True,
                text=True,
                timeout=60
            )
            output = result.stdout
            error = result.stderr
        except Exception as e:
            output, error = "", f"Execution failed: {str(e)}"

        # 📝 حفظ بالتاريخ
        entry = {
            "filename": file.filename,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "output": output,
            "error": error
        }
        history.insert(0, entry)

        # حفظ JSON
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    return render_template_string(HTML_TEMPLATE, history=history)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
