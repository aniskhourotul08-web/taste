import os
import re
import subprocess
import datetime
import json
import signal
from flask import Flask, request, render_template_string, redirect, url_for

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

# حفظ العمليات النشطة
processes = {}

# مكتبات بايثون المدمجة (لا نثبتها)
BUILTIN_LIBS = {"os", "sys", "re", "subprocess", "flask", "json", "datetime", "signal"}

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
        .container { max-width: 1000px; margin: 30px auto; padding: 20px; }
        .card { background: white; border-radius: 16px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); padding: 20px; margin-bottom: 20px; }
        h1 { margin: 0; font-size: 28px; }
        h2 { margin-bottom: 10px; color: #333; }
        input[type=file] { margin: 15px 0; padding: 8px; }
        button { background: #4f46e5; color: white; padding: 6px 12px; border: none;
                 border-radius: 8px; cursor: pointer; font-weight: bold; transition: 0.3s; margin-right: 5px; }
        button:hover { background: #4338ca; }
        pre { background: #111827; color: #10b981; padding: 15px; border-radius: 10px; overflow-x: auto; font-size: 14px; }
        .error { color: #ef4444; }
        .history-item { padding: 15px; border-left: 4px solid #4f46e5; margin-bottom: 15px; background: #fafafa; border-radius: 10px; }
        .timestamp { font-size: 12px; color: #6b7280; }
        .actions { margin-top: 10px; }
    </style>
</head>
<body>
    <header>
        <h1>🚀 Python Runner Pro</h1>
        <p>ارفع ملفات بايثون، يتم تثبيت المتطلبات وتشغيلها وإدارتها مع حفظ التاريخ</p>
    </header>
    <div class="container">

        <!-- Form -->
        <div class="card">
            <h2>📂 Upload Python File</h2>
            <form method="POST" enctype="multipart/form-data">
                <input type="file" name="file" required>
                <br>
                <button type="submit">Upload</button>
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
                <div class="actions">
                    <a href="{{ url_for('run_file', filename=item.filename) }}"><button>▶️ Run</button></a>
                    <a href="{{ url_for('stop_file', filename=item.filename) }}"><button>⏹ Stop</button></a>
                    <a href="{{ url_for('delete_file', filename=item.filename) }}"><button>🗑 Delete</button></a>
                </div>
                {% if item.output %}
                <h4>✅ Last Output:</h4>
                <pre>{{ item.output }}</pre>
                {% endif %}
                {% if item.error %}
                <h4 class="error">⚠️ Last Error:</h4>
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
                if lib not in BUILTIN_LIBS:
                    imports.add(lib)
    return imports

# 📦 تثبيت المتطلبات وعرضها كـ Console
def install_requirements():
    logs = []
    process = subprocess.Popen(
        [os.sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    for line in process.stdout:
        logs.append(line.strip())
    return "\n".join(logs)

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
        if imports:
            with open("requirements.txt", "a") as f:
                for lib in imports:
                    f.write(f"{lib}\n")
            logs = install_requirements()
        else:
            logs = "No new requirements needed."

        entry = {
            "filename": file.filename,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "output": logs,
            "error": ""
        }
        history.insert(0, entry)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    return render_template_string(HTML_TEMPLATE, history=history)

# ▶️ تشغيل ملف
@app.route("/run/<filename>")
def run_file(filename):
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(filepath):
        return redirect(url_for("upload_file"))

    process = subprocess.Popen(
        [os.sys.executable, filepath],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    processes[filename] = process

    output, error = process.communicate(timeout=30)
    entry = {
        "filename": filename,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "output": output,
        "error": error
    }
    history.insert(0, entry)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    return redirect(url_for("upload_file"))

# ⏹ إيقاف ملف
@app.route("/stop/<filename>")
def stop_file(filename):
    if filename in processes:
        processes[filename].terminate()
        del processes[filename]
    return redirect(url_for("upload_file"))

# 🗑 حذف ملف
@app.route("/delete/<filename>")
def delete_file(filename):
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    history[:] = [h for h in history if h["filename"] != filename]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    return redirect(url_for("upload_file"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
