from os import remove
from pathlib import Path
from uuid import uuid4

from flask import Flask, app, render_template, request
from flask_cors import CORS
from werkzeug.datastructures import FileStorage

from .extract import extract_text
from .chatbot import responder, ResponseType

app = Flask(__name__)
CORS(app)
BASE_PATH = Path(__file__).resolve(strict=True).parent.parent
TMP = BASE_PATH / "tmp"

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/process")
def process() -> dict:
    file: FileStorage = request.files["file"]
    ext: str = file.filename.split('.')[-1]
    new_filename = f"{uuid4()}.{ext}"
    file_path = TMP / new_filename
    file.save(file_path)
    text: str = extract_text(file_path, ext)
    # data: dict = get_info(text)
    remove(file_path)
    return {"file": file.filename, "ext": ext, "saved_as": new_filename, "path": str(TMP / new_filename), "text": str(text), "data": data}

@app.post("/api/chatbot")
def chatbot() -> dict:
    req = {}
    if request.files.__len__() > 0:
        file: FileStorage = request.files["payload"]
        ext: str = file.filename.split('.')[-1]
        new_filename = f"{uuid4()}.{ext}"
        file_path = TMP / new_filename
        file.save(file_path)
        req["type"] = ResponseType.Attachment
        req["payload"] = file_path
    else:
        req = dict(request.get_json())
    res = responder(req or "")
    return {**res}