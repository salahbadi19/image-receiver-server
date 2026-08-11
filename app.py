import os
import json
import uuid
import secrets
import datetime
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory, send_file, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ============ إعدادات ============
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
DB_FILE = BASE_DIR / "db.json"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# مفتاح API للوحة A - غيّره في Render Environment Variables
API_KEY = os.environ.get("API_KEY", "CHANGE_THIS_API_KEY")

app = Flask(__name__)
CORS(app)  # مهم للوحة A القادمة من دومين مختلف

# ============ دوال مساعدة ============

def same(a, b):
    return secrets.compare_digest(str(a).encode("utf-8"), str(b).encode("utf-8"))

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def load_db():
    if not DB_FILE.exists():
        return {"images": []}
    try:
        return json.loads(DB_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"images": []}

def save_db(db):
    DB_FILE.write_text(
        json.dumps(db, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def serialize_image(item):
    return {
        "id": item["id"],
        "name": item["name"],
        "filename": item["filename"],
        "url": f"/images/{item['filename']}",
        "source": item.get("source", "جهاز خارجي"),
        "created": item.get("created"),
        "viewed": item.get("viewed", False),
    }

# ============ لوحة التحكم HTML ============

DASHBOARD_HTML = r"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>لوحة الصور</title>
    <style>
        *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
        html,body{margin:0;padding:0}
        body{background:#fff;color:#0b0f16;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,Arial,sans-serif}
        button{font:inherit}
        .app{max-width:760px;margin:auto;padding:18px 16px calc(135px + env(safe-area-inset-bottom))}
        .topbar{position:sticky;top:0;z-index:40;background:rgba(255,255,255,.86);backdrop-filter:blur(18px);padding:8px 0 14px;display:flex;align-items:center;justify-content:flex-start}
        .title h1{margin:0;font-size:31px;line-height:1.05;font-weight:950;letter-spacing:-.03em}
        .title p{margin:7px 0 0;color:#667085;font-size:13px;font-weight:650}
        .page{display:none}
        .page.active{display:block;animation:pageFade .28s ease}
        @keyframes pageFade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
        .empty{border:1.5px dashed rgba(0,0,0,.16);background:linear-gradient(180deg,#fff,#fbfcfe);border-radius:30px;padding:56px 22px;text-align:center;box-shadow:0 18px 45px rgba(15,23,42,.05)}
        .empty-icon{width:76px;height:76px;margin:0 auto 14px;border-radius:26px;background:#fff;border:1.5px solid rgba(0,0,0,.08);display:grid;place-items:center;box-shadow:0 14px 30px rgba(15,23,42,.06)}
        .empty-icon svg{width:34px;height:34px;fill:none;stroke:#000;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
        .empty-title{font-size:18px;font-weight:900;color:#000}
        .empty-desc{margin-top:8px;color:#667085;font-size:13px;line-height:1.7;font-weight:600}
        .cards{display:grid;gap:18px}
        .card{background:#fff;border:1px solid #e9edf3;border-radius:30px;overflow:hidden;box-shadow:0 18px 45px rgba(15,23,42,.06);animation:cardIn .35s cubic-bezier(.2,.8,.2,1)}
        @keyframes cardIn{from{opacity:0;transform:translateY(16px) scale(.99)}to{opacity:1;transform:translateY(0) scale(1)}}
        .card-media{position:relative;padding:12px}
        .card-media img{width:100%;height:250px;object-fit:cover;display:block;border-radius:24px;background:#f8fafc;border:1px solid #e9edf3}
        .tag{position:absolute;top:24px;inset-inline-start:24px;z-index:2;padding:8px 12px;border-radius:999px;background:rgba(255,255,255,.88);backdrop-filter:blur(12px);border:1px solid rgba(0,0,0,.06);font-size:12px;font-weight:900;box-shadow:0 10px 22px rgba(15,23,42,.08)}
        .media-check{position:absolute;top:24px;inset-inline-end:24px;z-index:2;width:44px;height:44px;border:1.5px solid #000;background:rgba(255,255,255,.88);backdrop-filter:blur(12px);border-radius:16px;display:grid;place-items:center;cursor:pointer;box-shadow:0 12px 24px rgba(15,23,42,.08);transition:.2s ease}
        .media-check:active{transform:scale(.94)}
        .media-check svg{width:21px;height:21px;fill:none;stroke:#000;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}
        .card-body{padding:6px 16px 0}
        .card-name{font-size:17px;font-weight:900;word-break:break-word;letter-spacing:-.02em}
        .card-meta{margin-top:7px;color:#667085;font-size:12.5px;font-weight:650}
        .card-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:14px 16px 16px}
        .card-actions.one{grid-template-columns:1fr}
        .action{min-height:52px;border:1.5px solid #000;background:#fff;color:#000;border-radius:18px;display:flex;align-items:center;justify-content:center;gap:9px;font-size:14px;font-weight:900;cursor:pointer;transition:.2s ease;box-shadow:0 12px 24px rgba(15,23,42,.04)}
        .action:active{transform:scale(.98);background:#fbfbfc}
        .action svg{width:21px;height:21px;fill:none;stroke:#000;stroke-width:2.1;stroke-linecap:round;stroke-linejoin:round}
        .bottom-nav{position:fixed;inset-inline:0;bottom:0;z-index:60;padding:10px 16px calc(10px + env(safe-area-inset-bottom));background:rgba(255,255,255,.86);backdrop-filter:blur(20px);border-top:1px solid rgba(15,23,42,.05)}
        .bottom-nav-inner{max-width:760px;margin:auto;display:flex;gap:10px;background:#fff;border:1px solid #e9edf3;border-radius:28px;padding:8px;box-shadow:0 20px 45px rgba(15,23,42,.08)}
        .nav-item{flex:1;position:relative;border:none;background:transparent;border-radius:22px;min-height:64px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:7px;font-size:12.5px;font-weight:900;color:#0b0f16;cursor:pointer;transition:.22s ease}
        .nav-item.active{background:#f6f8fa;box-shadow:inset 0 0 0 1px #edf1f5}
        .nav-icon{position:relative;width:28px;height:28px;display:grid;place-items:center}
        .nav-icon svg{width:28px;height:28px;fill:none;stroke:#000;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
        .badge{position:absolute;top:-8px;inset-inline-end:-9px;min-width:20px;height:20px;padding:0 5px;border-radius:999px;background:#ff3b30;color:#fff;display:none;place-items:center;font-size:11px;font-weight:900;box-shadow:0 0 0 3px #fff}
        .badge.show{display:grid}
        .badge.pop{animation:badgePop .35s cubic-bezier(.2,.8,.2,1)}
        @keyframes badgePop{0%{transform:scale(.4)}60%{transform:scale(1.25)}100%{transform:scale(1)}}
        .toast{position:fixed;bottom:112px;left:50%;transform:translateX(-50%) translateY(18px);z-index:70;background:#fff;color:#000;border:1.5px solid #000;border-radius:16px;padding:12px 16px;font-size:13px;font-weight:900;opacity:0;pointer-events:none;transition:.25s ease;max-width:90%;text-align:center;box-shadow:0 18px 40px rgba(15,23,42,.10)}
        .toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
        @media (max-width:420px){.title h1{font-size:27px}.card-media img{height:210px}.action{font-size:13px}}
    </style>
</head>
<body>
    <div class="app">
        <header class="topbar">
            <div class="title">
                <h1>الصور</h1>
                <p id="subtitle">لا توجد صور جديدة</p>
            </div>
        </header>
        <main>
            <section class="page active" id="newPage">
                <div class="empty" id="newEmpty">
                    <div class="empty-icon"><svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="3"/><circle cx="8.5" cy="10.5" r="1.5"/><path d="M21 15l-4.5-4.5L7 20"/></svg></div>
                    <div class="empty-title">لا توجد صور جديدة</div>
                    <div class="empty-desc">عند وصول صورة جديدة ستظهر هنا.</div>
                </div>
                <div class="cards" id="newCards"></div>
            </section>
            <section class="page" id="oldPage">
                <div class="empty" id="oldEmpty">
                    <div class="empty-icon"><svg viewBox="0 0 24 24"><path d="M4 7h16"/><path d="M6 7l1.5-3h9L18 7"/><rect x="6" y="7" width="12" height="13" rx="3"/><path d="M10 11h4"/></svg></div>
                    <div class="empty-title">لا توجد صور قديمة</div>
                    <div class="empty-desc">عند الضغط على زر تم في الصور الجديدة ستنتقل الصور إلى هنا.</div>
                </div>
                <div class="cards" id="oldCards"></div>
            </section>
        </main>
    </div>
    <nav class="bottom-nav">
        <div class="bottom-nav-inner">
            <button type="button" class="nav-item active" id="newTab">
                <span class="nav-icon">
                    <svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="3"/><circle cx="8.5" cy="10.5" r="1.5"/><path d="M21 15l-4.5-4.5L7 20"/><path d="M18 2v6"/><path d="M15 5h6"/></svg>
                    <span class="badge" id="newBadge">0</span>
                </span>
                <span>الجديدة</span>
            </button>
            <button type="button" class="nav-item" id="oldTab">
                <span class="nav-icon">
                    <svg viewBox="0 0 24 24"><path d="M4 7h16"/><path d="M6 7l1.5-3h9L18 7"/><rect x="6" y="7" width="12" height="13" rx="3"/><path d="M10 11h4"/></svg>
                </span>
                <span>القديمة</span>
            </button>
        </div>
    </nav>
    <div class="toast" id="toast"></div>
    <script>
        const API_BASE = window.location.origin;
        let newImages = [], oldImages = [], activePage = "new";
        const newPage=document.getElementById("newPage"),oldPage=document.getElementById("oldPage"),newTab=document.getElementById("newTab"),oldTab=document.getElementById("oldTab"),newCards=document.getElementById("newCards"),oldCards=document.getElementById("oldCards"),newEmpty=document.getElementById("newEmpty"),oldEmpty=document.getElementById("oldEmpty"),newBadge=document.getElementById("newBadge"),subtitle=document.getElementById("subtitle"),toast=document.getElementById("toast");
        const icons={download:'<svg viewBox="0 0 24 24"><path d="M12 4v10"/><path d="M8 11l4 4 4-4"/><path d="M5 20h14"/></svg>',trash:'<svg viewBox="0 0 24 24"><path d="M5 7h14"/><path d="M9 7V5h6v2"/><path d="M7 7l1 13h8l1-13"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>',check:'<svg viewBox="0 0 24 24"><path d="M5 13l4 4L19 7"/></svg>'};
        function showToast(m){toast.textContent=m;toast.classList.add("show");setTimeout(()=>toast.classList.remove("show"),2300)}
        function formatDateTime(d){return new Intl.DateTimeFormat("ar",{dateStyle:"short",timeStyle:"short"}).format(d)}
        function newCountText(c){if(c===0)return"لا توجد صور جديدة";if(c===1)return"صورة واحدة جديدة";if(c===2)return"صورتان جديدتان";if(c<=10)return c+" صور جديدة";return c+" صورة جديدة"}
        function oldCountText(c){if(c===0)return"لا توجد صور قديمة";if(c===1)return"صورة واحدة قديمة";if(c===2)return"صورتان قديمتان";if(c<=10)return c+" صور قديمة";return c+" صورة قديمة"}
        function updateSubtitle(){subtitle.textContent=activePage==="new"?newCountText(newImages.length):oldCountText(oldImages.length)}
        function updateBadge(){const c=newImages.length;newBadge.textContent=c;if(c>0){newBadge.classList.add("show");newBadge.classList.remove("pop");void newBadge.offsetWidth;newBadge.classList.add("pop")}else{newBadge.classList.remove("show","pop")}}
        function showPage(p){activePage=p;if(p==="new"){newPage.classList.add("active");oldPage.classList.remove("active");newTab.classList.add("active");oldTab.classList.remove("active")}else{oldPage.classList.add("active");newPage.classList.remove("active");oldTab.classList.add("active");newTab.classList.remove("active")}updateSubtitle()}
        function revokeIfNeeded(i){if(i.url&&i.url.startsWith("blob:"))URL.revokeObjectURL(i.url)}
        function makeActionButton(l,h,o){const b=document.createElement("button");b.type="button";b.className="action";b.innerHTML=h+`<span>${l}</span>`;b.addEventListener("click",o);return b}
        async function downloadImage(i){try{const r=await fetch(i.url);const b=await r.blob();const u=URL.createObjectURL(b);const a=document.createElement("a");a.href=u;a.download=i.name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),600);showToast("تم تنزيل الصورة")}catch(e){const a=document.createElement("a");a.href=i.url;a.download=i.name;a.target="_blank";document.body.appendChild(a);a.click();a.remove();showToast("تم فتح الصورة للتنزيل")}}
        async function deleteNew(id){const i=newImages.find(x=>x.id===id);if(!i)return;if(!confirm("هل تريد حذف هذه الصورة؟"))return;try{await fetch(API_BASE+"/api/images/"+id,{method:"DELETE"})}catch(e){}revokeIfNeeded(i);newImages=newImages.filter(x=>x.id!==id);renderAll();showToast("تم حذف الصورة")}
        async function deleteOld(id){const i=oldImages.find(x=>x.id===id);if(!i)return;if(!confirm("هل تريد حذف هذه الصورة؟"))return;try{await fetch(API_BASE+"/api/images/"+id,{method:"DELETE"})}catch(e){}revokeIfNeeded(i);oldImages=oldImages.filter(x=>x.id!==id);renderAll();showToast("تم حذف الصورة")}
        async function moveOld(id){const idx=newImages.findIndex(x=>x.id===id);if(idx===-1)return;try{await fetch(API_BASE+"/api/images/"+id+"/view",{method:"POST"})}catch(e){}const[item]=newImages.splice(idx,1);oldImages.unshift(item);renderAll();showToast("تم نقل الصورة إلى القديمة")}
        function createCard(i,t){const c=document.createElement("article");c.className="card";const m=document.createElement("div");m.className="card-media";const img=document.createElement("img");img.src=i.url;img.alt=i.name;if(t==="old")img.addEventListener("click",()=>window.open(i.url,"_blank"));const tag=document.createElement("span");tag.className="tag";tag.textContent=t==="new"?"جديدة":"قديمة";m.appendChild(img);m.appendChild(tag);if(t==="new"){const cb=document.createElement("button");cb.type="button";cb.className="media-check";cb.title="نقل إلى الصور القديمة";cb.innerHTML=icons.check;cb.addEventListener("click",()=>moveOld(i.id));m.appendChild(cb)}const b=document.createElement("div");b.className="card-body";const n=document.createElement("div");n.className="card-name";n.textContent=i.name;const mt=document.createElement("div");mt.className="card-meta";mt.textContent=formatDateTime(i.date)+" • "+i.source;b.appendChild(n);b.appendChild(mt);const a=document.createElement("div");a.className=t==="new"?"card-actions":"card-actions one";if(t==="new"){a.appendChild(makeActionButton("تنزيل",icons.download,()=>downloadImage(i)));a.appendChild(makeActionButton("حذف",icons.trash,()=>deleteNew(i.id)))}else{a.appendChild(makeActionButton("حذف",icons.trash,()=>deleteOld(i.id)))}c.appendChild(m);c.appendChild(b);c.appendChild(a);return c}
        function renderNew(){newCards.innerHTML="";newEmpty.style.display=newImages.length?"none":"block";newImages.forEach(i=>newCards.appendChild(createCard(i,"new")))}
        function renderOld(){oldCards.innerHTML="";oldEmpty.style.display=oldImages.length?"none":"block";oldImages.forEach(i=>oldCards.appendChild(createCard(i,"old")))}
        function renderAll(){renderNew();renderOld();updateBadge();updateSubtitle()}
        function mapServerImage(i){return{id:i.id,url:API_BASE+i.url,name:i.name,source:i.source||"جهاز خارجي",date:new Date(i.created)}}
        async function loadDashboardFromServer(){try{const[nr,or]=await Promise.all([fetch(API_BASE+"/api/images/new"),fetch(API_BASE+"/api/images/old")]);const nd=await nr.json();const od=await or.json();newImages=(nd.images||[]).map(mapServerImage);oldImages=(od.images||[]).map(mapServerImage);renderAll()}catch(e){console.error(e)}}
        async function pollNewImages(){try{const r=await fetch(API_BASE+"/api/images/new");const d=await r.json();let changed=false;(d.images||[]).forEach(s=>{const item=mapServerImage(s);if(!newImages.some(x=>x.id===item.id)&&!oldImages.some(x=>x.id===item.id)){newImages.unshift(item);changed=true}});if(changed)renderAll()}catch(e){}}
        newTab.addEventListener("click",()=>showPage("new"));
        oldTab.addEventListener("click",()=>showPage("old"));
        loadDashboardFromServer();
        setInterval(pollNewImages,3000);
    </script>
</body>
</html>"""

# ============ Routes ============

@app.route("/", methods=["GET"])
def home():
    return Response(DASHBOARD_HTML, mimetype="text/html")

@app.route("/api/upload", methods=["POST"])
def upload_image():
    key = request.headers.get("X-API-Key", "")
    if not same(key, API_KEY):
        return jsonify({"error": "Unauthorized"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    original_name = secure_filename(file.filename)
    if not allowed_file(original_name):
        return jsonify({"error": "File type not allowed"}), 400

    image_id = uuid.uuid4().hex
    ext = Path(original_name).suffix.lower()
    safe_filename = f"{image_id}{ext}"

    file.save(UPLOAD_DIR / safe_filename)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    record = {
        "id": image_id,
        "name": original_name or safe_filename,
        "filename": safe_filename,
        "source": request.form.get("source", "جهاز خارجي"),
        "created": now,
        "viewed": False,
    }

    db = load_db()
    db["images"].insert(0, record)
    save_db(db)

    return jsonify({"ok": True, "image": serialize_image(record)}), 201

@app.route("/api/images/new", methods=["GET"])
def get_new_images():
    db = load_db()
    images = [serialize_image(i) for i in db["images"] if not i.get("viewed", False)]
    return jsonify({"images": images})

@app.route("/api/images/old", methods=["GET"])
def get_old_images():
    db = load_db()
    images = [serialize_image(i) for i in db["images"] if i.get("viewed", False)]
    return jsonify({"images": images})

@app.route("/api/images/<image_id>/view", methods=["POST"])
def mark_image_viewed(image_id):
    db = load_db()
    for item in db["images"]:
        if item["id"] == image_id:
            item["viewed"] = True
            save_db(db)
            return jsonify({"ok": True, "image": serialize_image(item)})
    return jsonify({"error": "Image not found"}), 404

@app.route("/api/images/<image_id>", methods=["DELETE"])
def delete_image(image_id):
    db = load_db()
    for index, item in enumerate(db["images"]):
        if item["id"] == image_id:
            deleted = db["images"].pop(index)
            save_db(db)
            file_path = UPLOAD_DIR / deleted["filename"]
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    pass
            return jsonify({"ok": True})
    return jsonify({"error": "Image not found"}), 404

@app.route("/images/<filename>", methods=["GET"])
def serve_image(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# ============ التشغيل ============

if __name__ == "__main__":
    # Render يحدد PORT تلقائيًا
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
