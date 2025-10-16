import os, json
import numpy as np
from flask import Flask, request, render_template
from tensorflow.keras.models import load_model, Model
from tensorflow.keras.preprocessing.image import img_to_array
from PIL import Image, ImageOps
import cv2

# ---------------- Configuration ----------------
MODEL_PATH = "thai_textile_model.h5"
CLASS_JSON = "class_names.json"
PP_JSON = "preprocess.json"

# Thresholds
THRESH_CONF    = 0.85
THRESH_MARGIN  = 0.20
THRESH_ENTROPY = 1.00
THRESH_SIM     = 0.70
THRESH_TEXTURE = 50.0

app = Flask(__name__)
# ไม่จำเป็นต้องใช้ UPLOAD_FOLDER อีกต่อไป แต่เก็บไว้เผื่ออนาคตได้
# app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")
# os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
ALLOWED = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# ---------------- Load Model ----------------
model = load_model(MODEL_PATH)

with open(CLASS_JSON, "r", encoding="utf-8") as f:
    CLASS_NAMES = json.load(f)

with open(PP_JSON, "r", encoding="utf-8") as f:
    PP = json.load(f)
IMAGE_SIZE = tuple(PP.get("image_size", [224, 224]))
RESCALE_DIV = float(PP.get("rescale_div", 255.0))
EXIF_FIX = bool(PP.get("exif_fix", True))

# Centroids (optional)
CENTROIDS = None
EMBED_MODEL = None
if os.path.exists("centroids.npy"):
    CENTROIDS = np.load("centroids.npy")
    EMBED_MODEL = Model(model.input, model.layers[-2].output)

# Textile info
from textile_info import TEXTILE_INFO


# ---------------- Helper Functions ----------------
def preprocess_pil(pil_img):
    if EXIF_FIX:
        pil_img = ImageOps.exif_transpose(pil_img)
    pil_img = pil_img.convert("RGB").resize(IMAGE_SIZE, Image.BILINEAR)
    arr = img_to_array(pil_img) / RESCALE_DIV
    return np.expand_dims(arr, axis=0)


def softmax_entropy(probs):
    eps = 1e-12
    return float(-np.sum(probs * np.log(probs + eps)))


def cosine_sim(a, b):
    a = a / (np.linalg.norm(a) + 1e-12)
    b = b / (np.linalg.norm(b) + 1e-12)
    return float(np.dot(a, b))

# ✅ [แก้ไข] ฟังก์ชันนี้ถูกสร้างขึ้นใหม่เพื่ออ่านภาพจาก stream สำหรับ OpenCV
def texture_score_from_stream(stream):
    """Calculates texture score from an image stream."""
    stream.seek(0)  # กลับไปที่จุดเริ่มต้นของ stream
    file_bytes = np.asarray(bytearray(stream.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0.0
    return float(cv2.Laplacian(img, cv2.CV_64F).var())


def should_reject(probs, tex, emb=None, idx=None):
    top1 = float(np.max(probs))
    srt = np.sort(probs)[::-1]
    margin = float(srt[0] - srt[1]) if len(srt) > 1 else srt[0]
    ent = softmax_entropy(probs)

    cond = (top1 < THRESH_CONF) or (margin < THRESH_MARGIN) or (ent > THRESH_ENTROPY) or (tex < THRESH_TEXTURE)

    sim = None
    if (CENTROIDS is not None) and (emb is not None) and (idx is not None):
        sim = cosine_sim(emb, CENTROIDS[idx])
        cond = cond or (sim < THRESH_SIM)

    return cond, top1, margin, ent, tex, sim

# ✅ [แก้ไข] เปลี่ยนชื่อฟังก์ชันจาก predict_path เป็น predict_stream
# และปรับโค้ดให้รับ stream และ filename แทน path
def predict_stream(stream, filename):
    """Runs prediction on an image stream."""
    tex = texture_score_from_stream(stream)

    stream.seek(0) # กลับไปที่จุดเริ่มต้นของ stream เพื่อให้ PIL อ่านได้
    pil = Image.open(stream)
    x = preprocess_pil(pil)

    probs = model.predict(x, verbose=0)[0]
    idx = int(np.argmax(probs))
    emb = EMBED_MODEL.predict(x, verbose=0)[0] if EMBED_MODEL is not None else None

    reject, top1, margin, ent, tex, sim = should_reject(probs, tex, emb, idx)

    # ดึง top-7 classes
    sorted_idx = np.argsort(probs)[::-1][:7]
    top7 = []
    for i in sorted_idx:
        cname = CLASS_NAMES[i]
        info = TEXTILE_INFO.get(cname, {})
        top7.append({
            "class_id": cname,
            "label_th": info.get("name_th", cname),
            "prob": float(probs[i]) * 100.0
        })

    # Reject unknown
    if reject:
        return {
            "unknown": True,
            "class_id": "UNKNOWN",
            "label_th": "ไม่พบลวดลายผ้าไทยในฐานข้อมูล",
            "confidence": top1,
            "filename": filename, # ใช้ชื่อไฟล์เดิม
            "slug": None,
            "top7": top7
        }

    cname = CLASS_NAMES[idx]
    info = TEXTILE_INFO.get(cname, {})
    return {
        "unknown": False,
        "class_id": cname,
        "label_th": info.get("name_th", cname),
        "province": info.get("province", "-"),
        "region": info.get("region", "-"),
        "confidence": float(probs[idx]),
        "filename": filename, # ใช้ชื่อไฟล์เดิม
        "slug": info.get("slug"),
        "top7": top7
    }



# ---------------- Routes ----------------
@app.route('/')
def home():
    return render_template("home.html")

# ✅ [แก้ไข] อัปเดต Route analyzer ให้ประมวลผลไฟล์ใน memory
@app.route('/analyzer', methods=["GET", "POST"])
def analyzer():
    results = []
    if request.method == "POST":
        files = request.files.getlist("images")
        for f in files:
            if not f or f.filename == "":
                continue
            
            ext = os.path.splitext(f.filename)[1].lower()
            if ext not in ALLOWED:
                continue

            # --- ไม่มีการบันทึกไฟล์อีกต่อไป ---
            # fname = f"{uuid.uuid4().hex}{ext}"
            # save = os.path.join(app.config["UPLOAD_FOLDER"], fname)
            # f.save(save)
            
            # ส่ง stream ของไฟล์ (f.stream) และชื่อไฟล์ (f.filename) ไปประมวลผลโดยตรง
            pred = predict_stream(f.stream, f.filename)
            results.append(pred)
            
    return render_template("analyzer.html", results=results)


@app.route("/database")
def database():
    return render_template("database.html", textiles=TEXTILE_INFO)


@app.route("/details/<fabric_name>")
def fabric_detail(fabric_name):
    for info in TEXTILE_INFO.values():
        if info.get("slug") == fabric_name:
            try:
                return render_template(f"details/{fabric_name}.html", fabric=info)
            except:
                return f"ไม่พบไฟล์ details/{fabric_name}.html", 404
    return "ไม่พบลายผ้า", 404



@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/technology")
def technology():
    return render_template("technology.html")


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)