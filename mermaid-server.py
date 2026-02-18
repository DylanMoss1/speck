"""Bidirectional Mermaid diagram server.

Serves a split-pane Mermaid editor at localhost that stays in sync with local files.
- External file edits are detected and pushed to the browser.
- Browser edits auto-save back to the file after a short debounce.
- Supports toggling between high-level and low-level diagram views.

Usage:
    python3 mermaid-server.py [HIGH_FILE] [LOW_FILE] [PORT]
    python3 mermaid-server.py diagram_high.mmd diagram_low.mmd 8765
"""

import http.server
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

HOST = "localhost"
DEFAULT_PORT = 8765
DEFAULT_HIGH_FILE = "diagram_high.mmd"
DEFAULT_LOW_FILE = "diagram_low.mmd"

DEFAULT_DIAGRAM = """\
graph TB
    A[Start] --> B[End]
"""

HTML_PAGE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Mermaid Editor</title>
<style>
  :root {
    --bg: #1e1e2e;
    --editor-bg: #181825;
    --preview-bg: #1e1e2e;
    --border: #313244;
    --text: #cdd6f4;
    --text-dim: #6c7086;
    --accent: #89b4fa;
    --green: #a6e3a1;
    --red: #f38ba8;
    --header-bg: #11111b;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg); color: var(--text);
    width: 100vw; height: 100vh; overflow: hidden;
    display: flex; flex-direction: column;
  }
  header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 16px; background: var(--header-bg);
    border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  header h1 { font-size: 14px; font-weight: 600; color: var(--text-dim); }
  #status {
    font-size: 12px; font-family: monospace;
    padding: 2px 8px; border-radius: 3px;
  }
  #toggle-level {
    font-size: 12px; font-family: monospace;
    padding: 4px 12px; border-radius: 4px;
    border: 1px solid var(--border);
    background: var(--editor-bg); color: var(--text);
    cursor: pointer; transition: background 0.15s, border-color 0.15s;
  }
  #toggle-level:hover {
    background: var(--border); border-color: var(--accent);
  }
  .header-right { display: flex; align-items: center; gap: 12px; }
  .status-saved { color: var(--green); }
  .status-saving { color: var(--accent); }
  .status-error { color: var(--red); }
  .status-reload { color: var(--accent); }

  .panes {
    display: flex; flex: 1; overflow: hidden;
  }
  .editor-pane {
    width: 40%; display: flex; flex-direction: column;
    border-right: 1px solid var(--border);
  }
  .pane-header {
    font-size: 11px; font-weight: 600; color: var(--text-dim);
    padding: 6px 12px; background: var(--header-bg);
    border-bottom: 1px solid var(--border);
    text-transform: uppercase; letter-spacing: 0.5px;
  }
  #editor {
    flex: 1; width: 100%; resize: none; border: none; outline: none;
    background: var(--editor-bg); color: var(--text);
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
    font-size: 14px; line-height: 1.6;
    padding: 12px 16px; tab-size: 4;
  }
  .preview-pane {
    flex: 1; display: flex; flex-direction: column; overflow: hidden;
  }
  #preview {
    flex: 1; overflow: auto; padding: 24px;
    display: flex; align-items: center; justify-content: center;
    background: var(--preview-bg);
  }
  #preview svg { max-width: 100%; height: auto; }
  #error {
    display: none; padding: 12px 16px;
    font-family: monospace; font-size: 12px;
    color: var(--red); background: #1e1017;
    border-top: 1px solid #45222a;
    max-height: 120px; overflow: auto; white-space: pre-wrap;
  }

  .splitter {
    width: 4px; cursor: col-resize; background: var(--border);
    transition: background 0.15s;
  }
  .splitter:hover, .splitter.dragging { background: var(--accent); }
</style>
</head>
<body>

<header>
  <h1>MERMAID EDITOR</h1>
  <div class="header-right">
    <button id="toggle-level">High Level</button>
    <span id="status"></span>
  </div>
</header>

<div class="panes" id="panes">
  <div class="editor-pane" id="editorPane">
    <div class="pane-header">Source</div>
    <textarea id="editor" spellcheck="false"></textarea>
  </div>
  <div class="splitter" id="splitter"></div>
  <div class="preview-pane">
    <div class="pane-header">Preview</div>
    <div id="preview"></div>
    <pre id="error"></pre>
  </div>
</div>

<script type="module">
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';

mermaid.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'loose' });

// Preprocessor: auto-generates numbering and diff styling from annotations.
// Annotations (placed at the end of the .mmd file):
//   %% @numbered          — add (N) labels to all nodes
//   %% @modified A B      — highlight nodes as modified (blue)
//   %% @new A B           — highlight nodes as new (green)
//   %% @removed A B       — highlight nodes as removed (red, dashed)
// Any @modified/@new/@removed annotation implies @numbered.
function preprocess(code) {
  const annotations = { modified: new Set(), new: new Set(), removed: new Set() };
  let numbered = false;
  const cleanLines = [];

  for (const line of code.split('\n')) {
    const diffMatch = line.match(/^%%\s*@(modified|new|removed)\s+(.+)/);
    const numMatch = line.match(/^%%\s*@numbered\s*$/);
    if (diffMatch) {
      diffMatch[2].trim().split(/[\s,]+/).forEach(id => annotations[diffMatch[1]].add(id));
      numbered = true;
    } else if (numMatch) {
      numbered = true;
    } else {
      cleanLines.push(line);
    }
  }

  const hasDiff = annotations.modified.size || annotations.new.size || annotations.removed.size;
  if (!numbered && !hasDiff) return code;

  // Find all unique nodes with labels, in order of first appearance
  const nodeOrder = [];
  const seenNodes = new Set();
  const nodeDefRegex = /([A-Za-z_]\w*)\s*\[(?:"[^"]*"|[^\]]*)\]/g;

  for (const line of cleanLines) {
    nodeDefRegex.lastIndex = 0;
    let m;
    while ((m = nodeDefRegex.exec(line)) !== null) {
      if (!seenNodes.has(m[1])) {
        seenNodes.add(m[1]);
        nodeOrder.push(m[1]);
      }
    }
  }

  // Assign numbers
  const nums = {};
  nodeOrder.forEach((id, i) => { nums[id] = i + 1; });

  // Process lines: inject (N) into labels, track edges
  const edges = [];
  const processedNodes = new Set();
  const resultLines = [];
  const arrowRegex = /([A-Za-z_]\w*)(?:\s*\[(?:"[^"]*"|[^\]]*)\])?\s*(?:-->|-.->|==>)\s*(?:\|(?:"[^"]*"|[^|]*)\|)?\s*([A-Za-z_]\w*)/g;

  for (const line of cleanLines) {
    let newLine = line;

    for (const id of nodeOrder) {
      if (processedNodes.has(id)) continue;
      const quotedRe = new RegExp(`(\\b${id}\\s*\\[)"([^"]*)"(\\])`);
      const unquotedRe = new RegExp(`(\\b${id}\\s*\\[)([^"\\]]*)(\\])`);
      if (quotedRe.test(newLine)) {
        newLine = newLine.replace(quotedRe, `$1"$2 <span style='color:grey'>(${nums[id]})</span>"$3`);
        processedNodes.add(id);
      } else if (unquotedRe.test(newLine)) {
        newLine = newLine.replace(unquotedRe, `$1"$2 <span style='color:grey'>(${nums[id]})</span>"$3`);
        processedNodes.add(id);
      }
    }

    arrowRegex.lastIndex = 0;
    let em;
    while ((em = arrowRegex.exec(line)) !== null) {
      edges.push({ from: em[1], to: em[2] });
    }

    resultLines.push(newLine);
  }

  // Append diff styles
  if (hasDiff) {
    resultLines.push('');
    for (const id of annotations.modified) {
      resultLines.push(`    style ${id} fill:#cce5ff,stroke:#0d6efd,color:#000`);
    }
    for (const id of annotations.new) {
      resultLines.push(`    style ${id} fill:#d4edda,stroke:#28a745,color:#000`);
    }
    for (const id of annotations.removed) {
      resultLines.push(`    style ${id} fill:#f8d7da,stroke:#dc3545,stroke-dasharray:5,color:#000`);
    }
    edges.forEach((edge, i) => {
      if (annotations.new.has(edge.from) || annotations.new.has(edge.to)) {
        resultLines.push(`    linkStyle ${i} stroke:#28a745`);
      } else if (annotations.removed.has(edge.from) || annotations.removed.has(edge.to)) {
        resultLines.push(`    linkStyle ${i} stroke:#dc3545,stroke-dasharray:5`);
      }
    });
  }

  return resultLines.join('\n');
}

const editor = document.getElementById('editor');
const preview = document.getElementById('preview');
const errorEl = document.getElementById('error');
const statusEl = document.getElementById('status');
const toggleBtn = document.getElementById('toggle-level');

let currentLevel = 'high';
let currentVersion = null;
let dirty = false;
let saveTimer = null;
let renderCounter = 0;

// --- Status ---
function status(msg, cls) {
  statusEl.textContent = msg;
  statusEl.className = 'status-' + cls;
}

function updateToggleButton() {
  toggleBtn.textContent = currentLevel === 'high' ? 'High Level' : 'Low Level';
}

// --- Render ---
async function render(code) {
  const processed = preprocess(code);
  if (!processed.trim()) {
    preview.innerHTML = '';
    errorEl.style.display = 'none';
    return;
  }
  renderCounter++;
  const id = 'mermaid-' + renderCounter;
  try {
    const { svg } = await mermaid.render(id, processed);
    preview.innerHTML = svg;
    errorEl.style.display = 'none';
  } catch (e) {
    // mermaid.render may inject an error element; clean up
    const badEl = document.getElementById('d' + id);
    if (badEl) badEl.remove();
    errorEl.textContent = e.message || String(e);
    errorEl.style.display = 'block';
  }
}

// --- Server communication ---
async function loadFromServer() {
  const resp = await fetch('/diagram?level=' + currentLevel);
  const data = await resp.json();
  currentVersion = data.version;
  return data.content;
}

async function saveToServer(content) {
  const resp = await fetch('/diagram?level=' + currentLevel, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content })
  });
  const data = await resp.json();
  currentVersion = data.version;
  return data;
}

// --- Initial load ---
const content = await loadFromServer();
editor.value = content;
await render(content);
status('Loaded', 'saved');
updateToggleButton();

// --- Editor input: live preview + debounced save ---
editor.addEventListener('input', () => {
  dirty = true;
  render(editor.value);

  clearTimeout(saveTimer);
  saveTimer = setTimeout(async () => {
    try {
      status('Saving...', 'saving');
      await saveToServer(editor.value);
      dirty = false;
      status('Saved', 'saved');
    } catch (e) {
      status('Save failed', 'error');
    }
  }, 800);
});

// --- Tab key inserts spaces ---
editor.addEventListener('keydown', (e) => {
  if (e.key === 'Tab') {
    e.preventDefault();
    const start = editor.selectionStart;
    const end = editor.selectionEnd;
    editor.value = editor.value.substring(0, start) + '    ' + editor.value.substring(end);
    editor.selectionStart = editor.selectionEnd = start + 4;
    editor.dispatchEvent(new Event('input'));
  }
});

// --- Ctrl+S explicit save ---
editor.addEventListener('keydown', async (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault();
    clearTimeout(saveTimer);
    try {
      status('Saving...', 'saving');
      await saveToServer(editor.value);
      dirty = false;
      status('Saved', 'saved');
    } catch (e) {
      status('Save failed', 'error');
    }
  }
});

// --- Toggle between high/low level ---
toggleBtn.addEventListener('click', async () => {
  if (dirty) {
    clearTimeout(saveTimer);
    await saveToServer(editor.value);
    dirty = false;
  }
  currentLevel = currentLevel === 'high' ? 'low' : 'high';
  updateToggleButton();
  status('Loading...', 'reload');
  const content = await loadFromServer();
  editor.value = content;
  await render(content);
  status('Loaded', 'saved');
});

// --- Poll for external file changes ---
setInterval(async () => {
  try {
    const resp = await fetch('/diagram/version?level=' + currentLevel);
    const data = await resp.json();

    if (currentVersion !== null && data.version !== currentVersion && data.external && !dirty) {
      status('Reloading...', 'reload');
      const content = await loadFromServer();
      editor.value = content;
      await render(content);
      status('Reloaded', 'saved');
    }
  } catch {}
}, 1000);

// --- Resizable splitter ---
const splitter = document.getElementById('splitter');
const editorPane = document.getElementById('editorPane');
const panes = document.getElementById('panes');
let dragging = false;

splitter.addEventListener('mousedown', (e) => {
  dragging = true;
  splitter.classList.add('dragging');
  e.preventDefault();
});

window.addEventListener('mousemove', (e) => {
  if (!dragging) return;
  const rect = panes.getBoundingClientRect();
  const pct = ((e.clientX - rect.left) / rect.width) * 100;
  const clamped = Math.min(Math.max(pct, 15), 85);
  editorPane.style.width = clamped + '%';
});

window.addEventListener('mouseup', () => {
  if (dragging) {
    dragging = false;
    splitter.classList.remove('dragging');
  }
});
</script>
</body>
</html>
"""


class DiagramState:
    def __init__(self, path: Path):
        self.path = path
        self._last_written_mtime = None

        if not self.path.exists():
            self.path.write_text(DEFAULT_DIAGRAM)
            print(f"Created new diagram: {self.path}")

    def read(self):
        content = self.path.read_text()
        version = os.path.getmtime(self.path)
        return content, version

    def write(self, content: str):
        self.path.write_text(content)
        self._last_written_mtime = os.path.getmtime(self.path)

    def get_version(self):
        return os.path.getmtime(self.path)

    def is_external_change(self):
        mtime = os.path.getmtime(self.path)
        return mtime != self._last_written_mtime


def make_handler(states: dict[str, DiagramState]):
    class Handler(http.server.BaseHTTPRequestHandler):
        def _get_state(self):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            level = params.get("level", ["high"])[0]
            return states.get(level, states["high"]), parsed.path

        def do_GET(self):
            state, path = self._get_state()
            if path == "/":
                self._respond(200, "text/html", HTML_PAGE.encode())
            elif path == "/diagram":
                content, version = state.read()
                self._json(200, {"content": content, "version": version})
            elif path == "/diagram/version":
                version = state.get_version()
                external = state.is_external_change()
                self._json(200, {"version": version, "external": external})
            else:
                self._respond(404, "text/plain", b"Not found")

        def do_POST(self):
            state, path = self._get_state()
            if path == "/diagram":
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                state.write(body["content"])
                self._json(200, {"ok": True, "version": state.get_version()})
            else:
                self._respond(404, "text/plain", b"Not found")

        def _json(self, code, obj):
            data = json.dumps(obj).encode()
            self._respond(code, "application/json", data)

        def _respond(self, code, content_type, body):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    return Handler


def main():
    high_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_HIGH_FILE)
    low_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(DEFAULT_LOW_FILE)
    port = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_PORT

    states = {
        "high": DiagramState(high_path),
        "low": DiagramState(low_path),
    }
    handler = make_handler(states)

    server = http.server.ThreadingHTTPServer((HOST, port), handler)
    print(f"Mermaid editor:  http://{HOST}:{port}")
    print(f"High-level:      {high_path.resolve()}")
    print(f"Low-level:       {low_path.resolve()}")
    print(f"Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
