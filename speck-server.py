"""Custom .speck file visualizer.

Serves a browser-based SVG visualization of .speck module/function graphs.
Parses .speck files server-side and renders interactive SVG client-side.

Usage:
    python3 speck-server.py <root.speck> [PORT]
    python3 speck-server.py myapp/myapp.speck 8766
"""

import http.server
import json
import os
import re
import sys
from pathlib import Path

HOST = "localhost"
DEFAULT_PORT = 8766


# ---------- Parser ----------

def sort_children(children, child_deps):
    """Topological sort: dependents first (left), dependencies last (right)."""
    name_to_path = {cp.split("/")[-1]: cp for cp in children}

    in_deg = {cp: 0 for cp in children}
    adj = {cp: [] for cp in children}
    for cp in children:
        cname = cp.split("/")[-1]
        for dep_name in child_deps.get(cname, []):
            dep_path = name_to_path.get(dep_name)
            if dep_path:
                adj[cp].append(dep_path)
                in_deg[dep_path] += 1

    queue = [cp for cp in children if in_deg[cp] == 0]
    result = []
    while queue:
        node = queue.pop(0)
        result.append(node)
        for dep in adj[node]:
            in_deg[dep] -= 1
            if in_deg[dep] == 0:
                queue.append(dep)

    for cp in children:
        if cp not in result:
            result.append(cp)

    return result


def parse_speck_tree(root_file_str):
    """Recursively parse .speck files from root, returning graph data."""
    root_file = Path(root_file_str)
    root_name = root_file.parent.name

    modules = {}
    function_edges = []

    def parse_module(speck_file, mod_path, depth):
        if not speck_file.exists():
            return
        content = speck_file.read_text()
        file_dir = speck_file.parent

        children = []
        child_deps = {}
        fns = []

        for m in re.finditer(r'mod\s+(\w+)\s*\{([^}]*)\}', content):
            name = m.group(1)
            deps = [d.strip() for d in m.group(2).split(',') if d.strip()]
            child_path = f"{mod_path}/{name}"
            children.append(child_path)
            child_deps[name] = deps
            parse_module(file_dir / name / f"{name}.speck", child_path, depth + 1)

        for m in re.finditer(
            r'def\s+(\w+)\s*\([^)]*\)\s*->\s*[^{]*\{([^}]*)\}',
            content, re.DOTALL
        ):
            fn_name = m.group(1)
            body = m.group(2)
            fns.append(fn_name)

            for cm in re.finditer(r'([\w./-]+)::(\w+)', body):
                ref_path, ref_fn = cm.group(1), cm.group(2)
                resolved = os.path.normpath(
                    os.path.join(str(file_dir), ref_path)
                )
                function_edges.append([
                    f"{mod_path}::{fn_name}",
                    f"{resolved}::{ref_fn}"
                ])

        sorted_children = sort_children(children, child_deps)

        modules[mod_path] = {
            "name": mod_path.split("/")[-1],
            "path": mod_path,
            "children": sorted_children,
            "functions": fns,
            "depth": depth,
        }

    parse_module(root_file, root_name, 0)

    mod_edge_set = set()
    for src, tgt in function_edges:
        src_mod = src.rsplit("::", 1)[0]
        tgt_mod = tgt.rsplit("::", 1)[0]
        if src_mod != tgt_mod:
            mod_edge_set.add((src_mod, tgt_mod))

    return {
        "modules": modules,
        "function_edges": function_edges,
        "module_edges": [list(e) for e in mod_edge_set],
        "root": root_name,
    }


def get_speck_version(root_file):
    """Return max mtime of all .speck files under the root directory."""
    root_dir = Path(root_file).parent
    speck_files = list(root_dir.rglob("*.speck"))
    if not speck_files:
        return 0
    return max(f.stat().st_mtime for f in speck_files)


# ---------- HTML Page ----------

HTML_PAGE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Speck Viewer</title>
<style>
  :root {
    --bg: #1e1e2e;
    --mantle: #181825;
    --crust: #11111b;
    --surface0: #313244;
    --surface1: #45475a;
    --overlay0: #585b70;
    --text: #cdd6f4;
    --subtext0: #a6adc8;
    --text-dim: #6c7086;
    --blue: #89b4fa;
    --green: #a6e3a1;
    --red: #f38ba8;
    --header-bg: #11111b;
    --border: #313244;
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
  .header-right { display: flex; align-items: center; gap: 8px; }
  .hdr-btn {
    font-size: 12px; font-family: monospace;
    padding: 4px 12px; border-radius: 4px;
    border: 1px solid var(--border);
    background: var(--mantle); color: var(--text);
    cursor: pointer; transition: background 0.15s, border-color 0.15s;
  }
  .hdr-btn:hover { background: var(--border); border-color: var(--blue); }
  #status { font-size: 12px; font-family: monospace; color: var(--text-dim); }

  #canvas-container {
    flex: 1; overflow: hidden; background: var(--bg);
    cursor: grab; user-select: none;
  }
  #canvas-container:active { cursor: grabbing; }
  #diagram { display: block; }

  /* Module boxes — clickable */
  .module-box { stroke: var(--surface1); stroke-width: 1.5; cursor: pointer; }
  .module-box:hover { stroke: var(--blue); stroke-width: 2; }
  .depth-0 { fill: #1e1e2e; }
  .depth-1 { fill: #181825; }
  .depth-2 { fill: #11111b; }
  .depth-3 { fill: #1e1e2e; }
  .module-label {
    fill: var(--subtext0);
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 13px; font-weight: 600;
    pointer-events: none;
  }

  /* Function boxes */
  .fn-box rect { fill: var(--surface0); stroke: var(--overlay0); stroke-width: 1; }
  .fn-box text {
    fill: var(--text);
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 12px;
  }

  /* Module contents — animated show/hide */
  .mod-contents { transition: opacity 0.3s; }
  .mod-contents.collapsed { opacity: 0; pointer-events: none; }

  /* Arrows */
  .mod-arrow { fill: none; stroke: var(--green); stroke-width: 2; }
  #arrows { transition: opacity 0.15s; }
</style>
</head>
<body>

<header>
  <h1>SPECK VIEWER</h1>
  <div class="header-right">
    <button class="hdr-btn" id="btn-expand">Expand All</button>
    <button class="hdr-btn" id="btn-collapse">Collapse All</button>
    <span id="status"></span>
  </div>
</header>

<div id="canvas-container">
  <svg id="diagram" xmlns="http://www.w3.org/2000/svg"></svg>
</div>

<script>
'use strict';

// --- Constants ---
var PAD = 30;
var PAD_BOTTOM = 50;
var HEADER_H = 38;
var FN_H = 30;
var FN_GAP = 10;
var MOD_GAP = 60;
var SECTION_GAP = 20;
var FN_PAD_X = 14;
var MIN_MOD_W = 80;
var LABEL_SIZE = 13;
var FN_SIZE = 12;
var ARROW_W = 10;

var svg = document.getElementById('diagram');
var container = document.getElementById('canvas-container');
var statusEl = document.getElementById('status');

// --- Text measurement ---
var measureSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
measureSvg.style.cssText = 'position:absolute;visibility:hidden;width:0;height:0';
document.body.appendChild(measureSvg);
var measureEl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
measureEl.setAttribute('font-family', "'JetBrains Mono', 'Fira Code', monospace");
measureSvg.appendChild(measureEl);

function measureText(text, fontSize) {
  measureEl.setAttribute('font-size', fontSize);
  measureEl.textContent = text;
  return measureEl.getBBox().width;
}

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// --- Build tree from flat modules dict ---
function buildTree(g) {
  function build(modPath) {
    var mod = g.modules[modPath];
    return {
      name: mod.name, path: mod.path, depth: mod.depth,
      functions: mod.functions,
      childNodes: mod.children.map(build),
    };
  }
  return build(g.root);
}

// --- Layout: bottom-up sizing ---
function computeSize(node) {
  for (var i = 0; i < node.childNodes.length; i++) computeSize(node.childNodes[i]);
  var labelW = measureText(node.name, LABEL_SIZE) + 8;
  var fnMaxW = 0;
  for (var i = 0; i < node.functions.length; i++) {
    fnMaxW = Math.max(fnMaxW, measureText(node.functions[i], FN_SIZE) + 2 * FN_PAD_X);
  }
  var fnAreaH = node.functions.length > 0
    ? node.functions.length * FN_H + (node.functions.length - 1) * FN_GAP : 0;
  var childrenW = 0, childrenH = 0;
  for (var i = 0; i < node.childNodes.length; i++) {
    childrenW += node.childNodes[i].w;
    childrenH = Math.max(childrenH, node.childNodes[i].h);
  }
  if (node.childNodes.length > 1) childrenW += (node.childNodes.length - 1) * MOD_GAP;
  var secGap = (fnAreaH > 0 && childrenH > 0) ? SECTION_GAP : 0;
  var contentW = Math.max(labelW, fnMaxW, childrenW, MIN_MOD_W);
  node.w = contentW + 2 * PAD;
  node.h = HEADER_H + fnAreaH + secGap + childrenH + PAD_BOTTOM;
  node._fnAreaH = fnAreaH;
  node._secGap = secGap;
}

// --- Layout: top-down positioning ---
function computePositions(node, x, y, fb, mb) {
  node.x = x; node.y = y;
  mb[node.path] = { x: x, y: y, w: node.w, h: node.h };
  var innerX = x + PAD, innerY = y + HEADER_H, innerW = node.w - 2 * PAD;
  var fnY = innerY;
  for (var i = 0; i < node.functions.length; i++) {
    var fnId = node.path + '::' + node.functions[i];
    fb[fnId] = { x: innerX, y: fnY, w: innerW, h: FN_H, name: node.functions[i] };
    fnY += FN_H + FN_GAP;
  }
  var childY = innerY + node._fnAreaH + node._secGap;
  var childX = innerX;
  for (var i = 0; i < node.childNodes.length; i++) {
    computePositions(node.childNodes[i], childX, childY, fb, mb);
    childX += node.childNodes[i].w + MOD_GAP;
  }
}

// --- Arrow routing (unchanged) ---

function orthogonalPath(sx, sy, tx, ty) {
  // Orthogonal routing with rounded corners (Q bezier, radius R)
  var R = 6;
  var dx = tx - sx, dy = ty - sy;

  // Straight line cases
  if (Math.abs(dy) < 1) return 'M ' + sx + ' ' + sy + ' L ' + tx + ' ' + ty;
  if (Math.abs(dx) < 1) return 'M ' + sx + ' ' + sy + ' L ' + tx + ' ' + ty;

  if (Math.abs(dx) >= Math.abs(dy)) {
    // Horizontal-dominant: H → V → H
    var midX = (sx + tx) / 2;
    var r = Math.min(R, Math.abs(midX - sx), Math.abs(tx - midX), Math.abs(dy) / 2);
    r = Math.max(r, 0);
    var dv = dy > 0 ? 1 : -1;
    var dh = dx > 0 ? 1 : -1;
    var p = 'M ' + sx + ' ' + sy;
    p += ' L ' + (midX - dh * r) + ' ' + sy;
    p += ' Q ' + midX + ' ' + sy + ', ' + midX + ' ' + (sy + dv * r);
    p += ' L ' + midX + ' ' + (ty - dv * r);
    p += ' Q ' + midX + ' ' + ty + ', ' + (midX + dh * r) + ' ' + ty;
    p += ' L ' + tx + ' ' + ty;
    return p;
  } else {
    // Vertical-dominant: V → H → V
    var midY = (sy + ty) / 2;
    var r = Math.min(R, Math.abs(midY - sy), Math.abs(ty - midY), Math.abs(dx) / 2);
    r = Math.max(r, 0);
    var dh = dx > 0 ? 1 : -1;
    var dv = dy > 0 ? 1 : -1;
    var p = 'M ' + sx + ' ' + sy;
    p += ' L ' + sx + ' ' + (midY - dv * r);
    p += ' Q ' + sx + ' ' + midY + ', ' + (sx + dh * r) + ' ' + midY;
    p += ' L ' + (tx - dh * r) + ' ' + midY;
    p += ' Q ' + tx + ' ' + midY + ', ' + tx + ' ' + (midY + dv * r);
    p += ' L ' + tx + ' ' + ty;
    return p;
  }
}

function connectionPoints(s, t) {
  // Use gap between box edges to decide connection side.
  // This ensures side-by-side boxes (like client/application) always
  // connect horizontally even when heights differ dramatically.
  var hGap = Math.max(t.x - (s.x + s.w), s.x - (t.x + t.w), 0);
  var vGap = Math.max(t.y - (s.y + s.h), s.y - (t.y + t.h), 0);
  var sCx = s.x + s.w / 2, sCy = s.y + s.h / 2;
  var tCx = t.x + t.w / 2, tCy = t.y + t.h / 2;

  if (hGap >= vGap) {
    // Connect horizontally (boxes are side-by-side)
    if (tCx >= sCx) {
      return { sx: s.x + s.w, sy: sCy, tx: t.x - ARROW_W, ty: tCy };
    } else {
      return { sx: s.x, sy: sCy, tx: t.x + t.w + ARROW_W, ty: tCy };
    }
  } else {
    // Connect vertically (boxes are stacked).
    // Use shared X from horizontal overlap to avoid S-curve zigzags
    // when fn boxes have different widths.
    var overlapL = Math.max(s.x, t.x);
    var overlapR = Math.min(s.x + s.w, t.x + t.w);
    var sharedX = (overlapL < overlapR) ? (overlapL + overlapR) / 2 : (sCx + tCx) / 2;
    if (tCy >= sCy) {
      return { sx: sharedX, sy: s.y + s.h, tx: sharedX, ty: t.y - ARROW_W };
    } else {
      return { sx: sharedX, sy: s.y, tx: sharedX, ty: t.y + t.h + ARROW_W };
    }
  }
}

function isAncestorOf(ancestorId, descendantId) {
  return descendantId.startsWith(ancestorId + '/') ||
         descendantId.startsWith(ancestorId + '::');
}

function findBlockingBoxes(sx, sy, tx, ty, sourceId, targetId, obstacles) {
  var xMin = Math.min(sx, tx) + 2, xMax = Math.max(sx, tx) - 2;
  var yMin = Math.min(sy, ty) - 2, yMax = Math.max(sy, ty) + 2;
  var result = [];
  for (var i = 0; i < obstacles.length; i++) {
    var obs = obstacles[i];
    if (obs.id === sourceId || obs.id === targetId) continue;
    if (isAncestorOf(obs.id, sourceId) || isAncestorOf(obs.id, targetId)) continue;
    if (isAncestorOf(sourceId, obs.id) || isAncestorOf(targetId, obs.id)) continue;
    if (obs.x + obs.w <= xMin || obs.x >= xMax) continue;
    if (obs.y + obs.h <= yMin || obs.y >= yMax) continue;
    result.push(obs);
  }
  return result;
}

function reroutedPath(sx, sy, tx, ty, blocking, sourceBox) {
  var ROUTE_MARGIN = 15, OBS_GAP = 20, R = 6, MIN_RUNIN = 15;
  var topY = Math.min.apply(null, blocking.map(function(b){ return b.y; })) - ROUTE_MARGIN;
  var botY = Math.max.apply(null, blocking.map(function(b){ return b.y + b.h; })) + ROUTE_MARGIN;
  var avgY = (sy + ty) / 2;
  var routeY = (Math.abs(topY - avgY) <= Math.abs(botY - avgY)) ? topY : botY;
  var leftEdge = Math.min.apply(null, blocking.map(function(b){ return b.x; }));
  var rightEdge = Math.max.apply(null, blocking.map(function(b){ return b.x + b.w; }));
  var cx1 = Math.max(sx + 2, leftEdge - OBS_GAP);
  var cx2 = Math.min(tx - MIN_RUNIN, rightEdge + OBS_GAP);
  var r = Math.min(R, Math.abs(sy - routeY)/2, Math.abs(ty - routeY)/2,
                   Math.abs(cx1 - sx)/2, Math.abs(tx - cx2)/2, Math.abs(cx2 - cx1)/2);
  r = Math.max(r, 0);
  var d1 = routeY < sy ? -1 : 1;
  var d2 = ty > routeY ? 1 : -1;
  var p = 'M ' + sx + ' ' + sy;
  p += ' L ' + (cx1 - r) + ' ' + sy;
  p += ' Q ' + cx1 + ' ' + sy + ', ' + cx1 + ' ' + (sy + d1 * r);
  p += ' L ' + cx1 + ' ' + (routeY - d1 * r);
  p += ' Q ' + cx1 + ' ' + routeY + ', ' + (cx1 + r) + ' ' + routeY;
  p += ' L ' + (cx2 - r) + ' ' + routeY;
  p += ' Q ' + cx2 + ' ' + routeY + ', ' + cx2 + ' ' + (routeY + d2 * r);
  p += ' L ' + cx2 + ' ' + (ty - d2 * r);
  p += ' Q ' + cx2 + ' ' + ty + ', ' + (cx2 + r) + ' ' + ty;
  p += ' L ' + tx + ' ' + ty;
  return p;
}

function computeArrowPath(s, t, sourceId, targetId, obstacles) {
  var pts = connectionPoints(s, t);
  var blocking = findBlockingBoxes(pts.sx, pts.sy, pts.tx, pts.ty, sourceId, targetId, obstacles);
  if (blocking.length === 0) return orthogonalPath(pts.sx, pts.sy, pts.tx, pts.ty);
  return reroutedPath(pts.sx, pts.sy, pts.tx, pts.ty, blocking, s);
}

// --- Global state ---
var graph = null;
var treeRoot = null;
var fnBoxes = {};
var modBoxes = {};
var expanded = new Set();
var currentVersion = null;

// --- Visibility logic ---

function isModVisible(path) {
  var segments = path.split('/');
  if (segments.length <= 1) return true; // root always visible
  var current = segments[0];
  for (var i = 1; i < segments.length; i++) {
    if (!expanded.has(current)) return false;
    current += '/' + segments[i];
  }
  return true;
}

function isFnVisible(fnId) {
  var modPath = fnId.split('::')[0];
  return isModVisible(modPath) && expanded.has(modPath);
}

// Resolve a function edge endpoint to the most specific visible element
function resolveVisible(fnId) {
  var parts = fnId.split('::');
  var modPath = parts[0];
  var segments = modPath.split('/');
  var current = segments[0];
  // Walk from root down; stop at first non-expanded module
  for (var i = 0; i < segments.length - 1; i++) {
    if (!expanded.has(current)) return current;
    current = segments.slice(0, i + 2).join('/');
  }
  // current is now the full modPath
  if (expanded.has(current)) return fnId; // function is visible
  return current; // module is visible but collapsed
}

// Collect obstacles that are currently visible
function getVisibleObstacles() {
  var obs = [];
  for (var path in modBoxes) {
    if (isModVisible(path)) {
      obs.push({ id: path, x: modBoxes[path].x, y: modBoxes[path].y,
                 w: modBoxes[path].w, h: modBoxes[path].h });
    }
  }
  for (var fnId in fnBoxes) {
    if (isFnVisible(fnId)) {
      obs.push({ id: fnId, x: fnBoxes[fnId].x, y: fnBoxes[fnId].y,
                 w: fnBoxes[fnId].w, h: fnBoxes[fnId].h });
    }
  }
  return obs;
}

// --- Render static boxes (called once) ---
function renderDefs() {
  var h = '<defs>';
  h += '<marker id="arrow-mod" viewBox="0 0 10 7" refX="0" refY="3.5" ';
  h += 'markerWidth="12" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto-start-reverse">';
  h += '<polygon points="0 0, 10 3.5, 0 7" fill="#a6e3a1"/></marker>';
  h += '</defs>';
  return h;
}

function renderBoxes(node) {
  var h = '';
  var dc = 'depth-' + (node.depth % 4);
  // Module rect (clickable)
  h += '<rect class="module-box ' + dc + '" data-path="' + node.path + '" x="' + node.x +
       '" y="' + node.y + '" width="' + node.w + '" height="' + node.h + '" rx="6"/>';
  h += '<text class="module-label" x="' + (node.x + 10) + '" y="' + (node.y + 18) +
       '">' + esc(node.name) + '</text>';

  // Contents group (functions + children)
  h += '<g class="mod-contents" data-contents="' + node.path + '">';
  for (var i = 0; i < node.functions.length; i++) {
    var fn = node.functions[i];
    var fb = fnBoxes[node.path + '::' + fn];
    if (!fb) continue;
    h += '<g class="fn-box">';
    h += '<rect x="' + fb.x + '" y="' + fb.y + '" width="' + fb.w +
         '" height="' + fb.h + '" rx="4"/>';
    h += '<text x="' + (fb.x + fb.w/2) + '" y="' + (fb.y + fb.h/2) +
         '" text-anchor="middle" dominant-baseline="central">' + esc(fb.name) + '</text>';
    h += '</g>';
  }
  for (var i = 0; i < node.childNodes.length; i++) {
    h += renderBoxes(node.childNodes[i]);
  }
  h += '</g>';
  return h;
}

// --- Update visibility based on expanded set ---
function updateVisibility() {
  var groups = document.querySelectorAll('[data-contents]');
  for (var i = 0; i < groups.length; i++) {
    var path = groups[i].getAttribute('data-contents');
    if (expanded.has(path)) {
      groups[i].classList.remove('collapsed');
    } else {
      groups[i].classList.add('collapsed');
    }
  }
}

// --- Compute and render arrows based on current visibility ---
function updateArrows() {
  var obstacles = getVisibleObstacles();
  var edgeMap = {}; // deduplicate resolved edges

  for (var i = 0; i < graph.function_edges.length; i++) {
    var src = graph.function_edges[i][0];
    var tgt = graph.function_edges[i][1];
    var rSrc = resolveVisible(src);
    var rTgt = resolveVisible(tgt);
    if (rSrc === rTgt) continue; // internal edge
    var key = rSrc + '>' + rTgt;
    if (edgeMap[key]) continue;
    edgeMap[key] = { src: rSrc, tgt: rTgt };
  }

  var html = '';
  for (var key in edgeMap) {
    var edge = edgeMap[key];
    var sBox = edge.src.indexOf('::') !== -1 ? fnBoxes[edge.src] : modBoxes[edge.src];
    var tBox = edge.tgt.indexOf('::') !== -1 ? fnBoxes[edge.tgt] : modBoxes[edge.tgt];
    if (!sBox || !tBox) continue;

    var d = computeArrowPath(sBox, tBox, edge.src, edge.tgt, obstacles);
    html += '<path class="mod-arrow" d="' + d + '" marker-end="url(#arrow-mod)"/>';
  }

  document.getElementById('arrows').innerHTML = html;
}

// --- Click to expand/collapse modules ---
svg.addEventListener('click', function(e) {
  var rect = e.target.closest('.module-box');
  if (!rect) return;
  var path = rect.getAttribute('data-path');
  if (!path) return;

  if (expanded.has(path)) {
    // Collapse this and all descendants
    var toRemove = [];
    expanded.forEach(function(p) {
      if (p === path || p.startsWith(path + '/')) toRemove.push(p);
    });
    for (var i = 0; i < toRemove.length; i++) expanded.delete(toRemove[i]);
  } else if (e.ctrlKey || e.metaKey) {
    // Ctrl+click: expand entire subtree
    for (var modPath in graph.modules) {
      if (modPath === path || modPath.startsWith(path + '/')) {
        expanded.add(modPath);
      }
    }
  } else {
    expanded.add(path);
  }
  updateVisibility();
  updateArrows();
});

// --- Expand All / Collapse All ---
document.getElementById('btn-expand').addEventListener('click', function() {
  for (var path in graph.modules) expanded.add(path);
  updateVisibility();
  updateArrows();
});
document.getElementById('btn-collapse').addEventListener('click', function() {
  expanded.clear();
  expanded.add(graph.root);
  updateVisibility();
  updateArrows();
});

// --- Pan & Zoom ---
var vb = { x: 0, y: 0, w: 800, h: 600 };
var isPanning = false, panStart = {};

function updateViewBox() {
  svg.setAttribute('viewBox', vb.x + ' ' + vb.y + ' ' + vb.w + ' ' + vb.h);
}

function fitToScreen() {
  var pad = 40;
  var rect = container.getBoundingClientRect();
  var aspect = rect.width / rect.height;
  var contentW = treeRoot.w + 2 * pad;
  var contentH = treeRoot.h + 2 * pad;
  var contentAspect = contentW / contentH;
  if (contentAspect > aspect) {
    vb.w = contentW; vb.h = contentW / aspect;
  } else {
    vb.h = contentH; vb.w = contentH * aspect;
  }
  vb.x = -pad - (vb.w - treeRoot.w) / 2 + pad;
  vb.y = -pad - (vb.h - treeRoot.h) / 2 + pad;
  updateViewBox();
}

container.addEventListener('wheel', function(e) {
  e.preventDefault();
  var factor = e.deltaY > 0 ? 1.1 : 0.9;
  var r = svg.getBoundingClientRect();
  var mx = (e.clientX - r.left) / r.width;
  var my = (e.clientY - r.top) / r.height;
  var nw = vb.w * factor, nh = vb.h * factor;
  vb.x += (vb.w - nw) * mx; vb.y += (vb.h - nh) * my;
  vb.w = nw; vb.h = nh;
  updateViewBox();
}, { passive: false });

container.addEventListener('mousedown', function(e) {
  isPanning = true;
  panStart = { x: e.clientX, y: e.clientY, vx: vb.x, vy: vb.y };
});
window.addEventListener('mousemove', function(e) {
  if (!isPanning) return;
  var r = svg.getBoundingClientRect();
  vb.x = panStart.vx - (e.clientX - panStart.x) / r.width * vb.w;
  vb.y = panStart.vy - (e.clientY - panStart.y) / r.height * vb.h;
  updateViewBox();
});
window.addEventListener('mouseup', function() { isPanning = false; });

// --- Main load ---
async function loadAndRender() {
  var resp = await fetch('/graph');
  graph = await resp.json();
  treeRoot = buildTree(graph);
  computeSize(treeRoot);
  fnBoxes = {}; modBoxes = {};
  computePositions(treeRoot, 0, 0, fnBoxes, modBoxes);

  // Start with root expanded (shows top-level modules)
  expanded.clear();
  expanded.add(graph.root);

  svg.setAttribute('width', '100%');
  svg.setAttribute('height', '100%');
  svg.innerHTML = renderDefs() + '<g id="boxes">' + renderBoxes(treeRoot) + '</g><g id="arrows"></g>';

  updateVisibility();
  updateArrows();
  fitToScreen();
  statusEl.textContent = 'Loaded';
}

// --- Auto-reload ---
setInterval(async function() {
  try {
    var resp = await fetch('/graph/version');
    var data = await resp.json();
    if (currentVersion !== null && data.version !== currentVersion) {
      statusEl.textContent = 'Reloading...';
      await loadAndRender();
      currentVersion = data.version;
    } else if (currentVersion === null) {
      currentVersion = data.version;
    }
  } catch(e) {}
}, 1000);

loadAndRender().then(async function() {
  var resp = await fetch('/graph/version');
  var data = await resp.json();
  currentVersion = data.version;
});
</script>
</body>
</html>"""


# ---------- Server ----------

def make_handler(root_file):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                self._respond(200, "text/html", HTML_PAGE.encode())
            elif self.path == "/graph":
                graph = parse_speck_tree(root_file)
                self._json(200, graph)
            elif self.path == "/graph/version":
                version = get_speck_version(root_file)
                self._json(200, {"version": version})
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

        def log_message(self, fmt, *args):
            pass

    return Handler


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 speck-server.py <root.speck> [PORT]")
        sys.exit(1)

    root_file = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT

    if not Path(root_file).exists():
        print(f"Error: {root_file} not found")
        sys.exit(1)

    handler = make_handler(root_file)
    server = http.server.ThreadingHTTPServer((HOST, port), handler)
    print(f"Speck viewer:  http://{HOST}:{port}")
    print(f"Root file:     {Path(root_file).resolve()}")
    print(f"Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
