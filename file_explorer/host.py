import os
import socket
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn
from jinja2 import Template
import dotenv

dotenv.load_dotenv()

app = FastAPI()

# ---------- CONFIG ----------
DIR_ENV_KEY = "FILE_EXPLORER_BASE_DIR"
BASE_DIR = Path(os.getenv(DIR_ENV_KEY, Path.cwd()))

# ---------- TEMPLATE ----------
EXPLORER_TEMPLATE = Template("""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>File Explorer</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background:#fafafa; }
    .container { max-width: 980px; margin: 0 auto; background: white; padding:20px; border-radius:10px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }
    .top { display:flex; gap:8px; align-items:center; margin-bottom:12px; flex-wrap:wrap; }
    input[type="text"]{ flex:1; padding:8px; font-size:14px; border-radius:6px; border:1px solid #ccc; min-width:180px; }
    button { padding:8px 12px; border-radius:6px; border:none; background:#0b74de; color:white; font-size:14px; cursor:pointer; }
    a { text-decoration:none; color:#0b74de; }
    ul { list-style:none; padding-left:0; margin:0; }
    li { padding:12px 0; border-bottom:1px solid #f2f2f2; }
    ul.no-separators li { border-bottom:none; padding:0; margin:0; }
    ul.no-separators li .preview img,
    ul.no-separators li .preview video { margin-top:0; border-radius:0; }
    .meta { color:#666; font-size:13px; }
    .preview img, .preview video { width:100%; height:auto; border-radius:8px; margin-top:8px; display:block; }
  </style>
</head>
<body>
  <div class="container">
    <h2>📂 File Explorer — {{ rel_path_display }}</h2>

    <div class="top">
      <button id="backBtn">⬅ Back</button>

      <form id="pathForm" onsubmit="goToPath(event)" style="display:flex; gap:8px; flex:1;">
        <input id="pathInput" type="text" placeholder="Enter path (eg. subdir/nested)" value="{{ rel_path_display }}">
        <button type="submit">Go</button>
      </form>

      <button id="restoreBtn" style="display:none">Restore last</button>
      <button type="button" id="toggleSepBtn">Hide separators</button>
    </div>

    <ul id="listing">
    {% for f in files %}
      <li>
        {% if f.is_dir %}
          📁 <a class="dir-link" href="{{ f.link }}">{{ f.name }}/</a>
          <span class="meta"> (directory)</span>

        {% elif f.is_image %}
          <div class="preview">
            <img src="{{ f.file_link }}" alt="{{ f.name }}">
          </div>

        {% elif f.is_video %}
          <div class="preview">
            <video controls preload="none">
              <source src="{{ f.file_link }}">
              Your browser doesn't support the video tag.
            </video>
          </div>
          <div>
            <span>{{ f.name }}</span>
            <span class="meta"> — {{ f.size_human }} • {{ f.mtime }}</span>
          </div>

        {% else %}
          📄 <a class="file-link" href="{{ f.link }}" target="_blank" rel="noopener">{{ f.name }}</a>
          <span class="meta"> — {{ f.size_human }} • {{ f.mtime }}</span>
        {% endif %}
      </li>
    {% endfor %}
    </ul>
  </div>

<script>
  const currentRaw = {{ rel_path_raw|tojson }};
  try { localStorage.setItem('lastPath', currentRaw); } catch (e) {}

  // Restore last
  const restoreBtn = document.getElementById('restoreBtn');
  const last = (() => { try { return localStorage.getItem('lastPath'); } catch(e){return null;} })();
  if (last && last !== currentRaw) {
    restoreBtn.style.display = 'inline-block';
    restoreBtn.onclick = () => {
      if (!last || last === "") location.href = "/";
      else location.href = "/browse/" + encodeURIComponent(last);
    };
  }

  // Back = go up one level
  document.getElementById("backBtn").onclick = () => {
    let parts = currentRaw.split("/").filter(Boolean);
    if (parts.length === 0) { location.href = "/"; return; }
    parts.pop();
    let up = parts.join("/");
    if (up) location.href = "/browse/" + encodeURIComponent(up);
    else location.href = "/";
  };

  // Save last visited dir on click
  document.querySelectorAll('a.dir-link').forEach(a => {
    a.addEventListener('click', () => {
      try {
        const href = a.getAttribute('href') || '';
        const m = href.match(/^\\/browse\\/(.+)/);
        const p = m ? decodeURIComponent(m[1]) : '';
        localStorage.setItem('lastPath', p);
      } catch(e) {}
    });
  });

  // Go to typed path
  function goToPath(ev) {
    ev.preventDefault();
    const raw = (document.getElementById('pathInput').value || "").trim();
    const normalized = raw.replace(/^\\/+/, '');
    if (!normalized) window.location.href = "/";
    else window.location.href = "/browse/" + encodeURIComponent(normalized);
  }

  // Toggle separators
  const toggleBtn = document.getElementById("toggleSepBtn");
  const listing = document.getElementById("listing");
  toggleBtn.onclick = () => {
    listing.classList.toggle("no-separators");
    if (listing.classList.contains("no-separators")) {
      toggleBtn.textContent = "Show separators";
    } else {
      toggleBtn.textContent = "Hide separators";
    }
  };
</script>
</body>
</html>""")

# ---------- ROUTES ----------
def human_size(size):
    for unit in ['B','KB','MB','GB','TB']:
        if size < 1024.0: return f"{size:.1f} {unit}"
        size /= 1024.0

@app.get("/", response_class=HTMLResponse)
@app.get("/browse/{subpath:path}", response_class=HTMLResponse)
def browse(subpath: str = ""):
    abs_path = BASE_DIR / subpath
    if not abs_path.exists():
        raise HTTPException(404, "Path not found")
    if abs_path.is_file():
        return FileResponse(abs_path)

    files = []
    for entry in sorted(abs_path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
        stat = entry.stat()
        rel = os.path.relpath(entry, BASE_DIR)
        f = {
            "name": entry.name,
            "is_dir": entry.is_dir(),
            "is_image": entry.suffix.lower() in [".png",".jpg",".jpeg",".gif",".webp"],
            "is_video": entry.suffix.lower() in [".mp4",".webm",".ogg",".mov",".avi",".mkv"],
            "link": f"/browse/{rel}" if entry.is_dir() else f"/browse/{rel}",
            "file_link": f"/browse/{rel}" if entry.is_file() else None,
            "size_human": human_size(stat.st_size),
            "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
        }
        files.append(f)

    return EXPLORER_TEMPLATE.render(
        files=files,
        rel_path_display=subpath or ".",
        rel_path_raw=subpath
    )

# ---------- MAIN ----------
if __name__ == "__main__":
    print(f"📂 Hosting directory: {BASE_DIR.absolute()}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            print(f"✅ Server running at http://{ip}:8000\n\n\n")
    except Exception as exc:
        print("Error showing ipv4:", exc)

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
