# LANshare_Mark2.py

import argparse
import os
import time
import socket
import pathlib
import math
from werkzeug.utils import safe_join, secure_filename
from flask import (
    Flask, request, send_file, jsonify, render_template_string,
    abort, url_for, Response
)
from functools import wraps

# ---------- Config ----------
CHUNK_DIR_NAME = ".upload_chunks"  # temp folder inside shared folder
ALLOWED_EXTENSIONS = None  # None -> allow all
# ----------------------------

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = None  # no built-in limit


# ---------- Helpers ----------
def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def is_allowed(filename: str) -> bool:
    if ALLOWED_EXTENSIONS is None:
        return True
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext in ALLOWED_EXTENSIONS

def ensure_dirs(shared_folder):
    os.makedirs(shared_folder, exist_ok=True)
    os.makedirs(os.path.join(shared_folder, CHUNK_DIR_NAME), exist_ok=True)

def safe_path_join(shared_folder, filename):
    filename = secure_filename(filename)
    return safe_join(shared_folder, filename)
# ----------------------------


# ---------- Authentication ----------
def check_auth(username, password):
    return username == app.username and password == app.password

def authenticate():
    return Response(
        'Authentication required', 401,
        {'WWW-Authenticate': 'Basic realm="LANShare"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated
# ----------------------------


# ---------- Routes ----------
INDEX_HTML = """
<!doctype html>
<title>LANShare</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{font-family:system-ui,Segoe UI,Roboto,Arial;margin:18px;}
.container{max-width:900px;margin:auto}
h1{margin-bottom:6px}
#drop{border:2px dashed #888;padding:18px;border-radius:8px;text-align:center}
.filelist{margin-top:12px}
.item{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid #eee}
.progress{width:40%;min-width:120px}
button{padding:6px 10px;border-radius:6px}
</style>
<div class="container">
  <h1>LANShare</h1>
  <p>Open this URL on any device in the same Wi-Fi. Drag & drop files here to upload (resumable chunks).</p>
  <div id="drop">Drop files here or <input id="fileinput" type="file" multiple></div>
  <div id="status"></div>
  <div class="filelist" id="files"></div>
</div>

<script>
async function listFiles(){
  let r = await fetch("{{ list_url }}");
  let data = await r.json();
  const filesDiv = document.getElementById("files");
  filesDiv.innerHTML = "";
  if(data.length===0){ filesDiv.innerHTML = "<p>No files yet.</p>"; return; }
  data.forEach(f=>{
    const el = document.createElement('div'); el.className='item';
    const left = document.createElement('div'); left.innerHTML = `<strong>${f.name}</strong><div style="font-size:12px;color:#666">${f.size_readable}</div>`;
    const right = document.createElement('div');
    const dl = document.createElement('a'); dl.href = f.url; dl.textContent='Download'; dl.style.marginRight='8px';
    const del = document.createElement('button'); del.textContent='Delete';
    del.onclick = async ()=>{ if(!confirm('Delete '+f.name+'?')) return; await fetch(f.delete_url,{method:'POST'}); listFiles(); };
    right.appendChild(dl); right.appendChild(del);
    el.appendChild(left); el.appendChild(right);
    filesDiv.appendChild(el);
  });
}

function readableSize(n){
  const units=['B','KB','MB','GB','TB']; let i=0;
  while(n>=1024 && i<units.length-1){ n/=1024; i++; }
  return n.toFixed( (i===0)?0:2 ) + ' ' + units[i];
}

document.getElementById('fileinput').addEventListener('change', ev=>{
  uploadMany(ev.target.files);
});
const drop = document.getElementById('drop');
drop.addEventListener('dragover', ev=>{ ev.preventDefault(); drop.style.borderColor='#3b82f6';});
drop.addEventListener('dragleave', ev=>{ drop.style.borderColor='#888';});
drop.addEventListener('drop', ev=>{ ev.preventDefault(); drop.style.borderColor='#888'; uploadMany(ev.dataTransfer.files);});

async function uploadMany(list){
  for(const f of list){ await uploadFile(f); }
  listFiles();
}

async function uploadFile(file){
  const chunkSize = 1024*1024; // 1 MB
  const total = file.size;
  const id = encodeURIComponent(file.name);
  const statusResp = await fetch("{{ status_url }}?name="+id);
  let uploaded = 0;
  if(statusResp.ok){ const j = await statusResp.json(); uploaded = j.offset || 0; }
  const pdiv = document.createElement('div'); pdiv.className='item';
  pdiv.innerHTML = `<div>${file.name}</div><div class="progress"><progress value="${uploaded}" max="${total}" style="width:100%"></progress></div>`;
  document.getElementById('status').appendChild(pdiv);

  let pos = uploaded;
  while(pos < total){
    const chunk = file.slice(pos, pos+chunkSize);
    const form = new FormData();
    form.append('name', file.name);
    form.append('offset', pos);
    form.append('chunk', chunk);
    const r = await fetch("{{ upload_chunk_url }}", {method:'POST', body: form});
    if(!r.ok){ alert('Upload failed'); return; }
    pos = pos + chunk.size;
    pdiv.querySelector('progress').value = pos;
  }
  const fin = await fetch("{{ upload_finish_url }}", {method:'POST', body: JSON.stringify({name:file.name}), headers:{'Content-Type':'application/json'}});
  pdiv.remove();
}

window.onload = listFiles;
</script>
"""

@app.route("/")
@requires_auth
def index():
    return render_template_string(
        INDEX_HTML,
        base_path=app.shared_folder,
        list_url=url_for('list_files'),
        status_url=url_for('upload_status'),
        upload_chunk_url=url_for('upload_chunk'),
        upload_finish_url=url_for('upload_finish'),
    )

@app.route("/list.json")
@requires_auth
def list_files():
    files = []
    for fn in sorted(os.listdir(app.shared_folder)):
        if fn == CHUNK_DIR_NAME: continue
        path = os.path.join(app.shared_folder, fn)
        if os.path.isfile(path):
            size = os.path.getsize(path)
            files.append({
                "name": fn,
                "size": size,
                "size_readable": human_readable(size),
                "url": url_for('download_file', filename=fn),
                "delete_url": url_for('delete_file', filename=fn)
            })
    return jsonify(files)

@app.route("/upload_status")
@requires_auth
def upload_status():
    name = request.args.get('name')
    if not name:
        return jsonify({"offset": 0})
    safe_name = secure_filename(name)
    chunk_path = os.path.join(app.shared_folder, CHUNK_DIR_NAME, safe_name + ".part")
    offset = 0
    if os.path.exists(chunk_path):
        offset = os.path.getsize(chunk_path)
    real_path = os.path.join(app.shared_folder, safe_name)
    if os.path.exists(real_path):
        offset = os.path.getsize(real_path)
    return jsonify({"offset": offset})

@app.route("/upload_chunk", methods=['POST'])
@requires_auth
def upload_chunk():
    if 'chunk' not in request.files or 'name' not in request.form or 'offset' not in request.form:
        return ("bad request", 400)
    name = request.form['name']
    offset = int(request.form['offset'])
    f = request.files['chunk']
    safe_name = secure_filename(name)
    if not is_allowed(safe_name):
        return ("forbidden", 403)
    chunk_dir = os.path.join(app.shared_folder, CHUNK_DIR_NAME)
    os.makedirs(chunk_dir, exist_ok=True)
    part_path = os.path.join(chunk_dir, safe_name + ".part")
    current = os.path.getsize(part_path) if os.path.exists(part_path) else 0
    if current != offset:
        return jsonify({"ok": False, "offset": current}), 409
    with open(part_path, "ab") as out:
        chunk_stream = f.stream
        while True:
            data = chunk_stream.read(1024*1024)
            if not data:
                break
            out.write(data)
    return jsonify({"ok": True, "offset": os.path.getsize(part_path)})

@app.route("/upload_finish", methods=['POST'])
@requires_auth
def upload_finish():
    js = request.get_json(force=True)
    if not js or 'name' not in js: return ("bad request",400)
    name = secure_filename(js['name'])
    part_path = os.path.join(app.shared_folder, CHUNK_DIR_NAME, name + ".part")
    final_path = os.path.join(app.shared_folder, name)
    if not os.path.exists(part_path):
        return ("no part", 404)
    os.replace(part_path, final_path)
    return jsonify({"ok": True, "path": final_path})

@app.route("/delete/<path:filename>", methods=['POST'])
@requires_auth
def delete_file(filename=None):
    safe_name = secure_filename(filename)
    target = os.path.join(app.shared_folder, safe_name)
    if os.path.exists(target):
        os.remove(target)
    return jsonify({"ok": True})

@app.route("/download/<path:filename>")
@requires_auth
def download_file(filename=None):
    safe_name = secure_filename(filename)
    path = os.path.join(app.shared_folder, safe_name)
    if not os.path.exists(path):
        abort(404)
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))
# ----------------------------


# ---------- Utilities ----------
def human_readable(n):
    units = ['B','KB','MB','GB','TB']
    i = 0
    while n >= 1024 and i < len(units)-1:
        n /= 1024; i += 1
    return f"{n:.2f} {units[i]}"
# ----------------------------


# ---------- Run Server ----------
def run_server(shared_folder, port, bind, username, password):
    app.shared_folder = os.path.abspath(shared_folder)
    app.username = username
    app.password = password
    ensure_dirs(app.shared_folder)
    lan_ip = get_lan_ip() if bind in ("0.0.0.0", "", None) else bind
    print("=== LANShare ===")
    print(f"Shared folder: {app.shared_folder}")
    print(f"Access URL: http://{lan_ip}:{port}/  (login required)")
    app.run(host=bind or "0.0.0.0", port=port, threaded=True)

print("---------------------------------------------------------LAN SHARE IS STARTING---------------------------------------------------------")
print("---------------------------------------------------------A PROJECT BY RITIK-TRADEZ---------------------------------------------------------")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--folder", "-f", required=True, help="Folder to share")
    p.add_argument("--port", "-p", type=int, default=8000)
    p.add_argument("--bind", default="0.0.0.0", help="Bind address (0.0.0.0)")
    p.add_argument("--user", required=True, help="Username for auth")
    p.add_argument("--password", required=True, help="Password for auth")
    args = p.parse_args()
    run_server(args.folder, args.port, args.bind, args.user, args.password)
