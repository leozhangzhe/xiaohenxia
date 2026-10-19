"""Test-only browser capability fixture, never loaded by production routes.

Run with project Python. Prints one localhost URL, no secrets. Ctrl+C stops it.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import mimetypes

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "spiderfoot/static"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        path = urlsplit(self.path).path
        if path.startswith("/static/"):
            target = (STATIC / path.removeprefix("/static/")).resolve()
            if not target.is_relative_to(STATIC) or not target.is_file():
                self.send_error(404)
                return
            content = target.read_bytes()
            mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        else:
            mode = path.strip("/") or "normal"
            if mode not in {"normal", "reduced", "fallback"}:
                self.send_error(404)
                return
            force = ""
            if mode == "reduced":
                force = "const media=window.matchMedia.bind(window);window.matchMedia=q=>q.includes('prefers-reduced-motion')?Object.assign(new EventTarget(),{matches:true}):media(q);"
            elif mode == "fallback":
                force = "const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return type==='webgl'?null:get.call(this,type,...args)};"
            content = ("""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>背景能力隔离验证</title><link rel="stylesheet" href="/static/css/app-background.css">
<style>body{isolation:isolate;margin:0;background:#121212;color:#fafafa;font:16px/1.8 system-ui}main{max-width:600px;margin:16vh auto;padding:28px;background:#18181bf5;border-radius:18px}button,a{color:#fafafa;background:#282833;border:1px solid #888;padding:8px 16px;margin:8px;border-radius:8px}output{display:block;white-space:pre-wrap;overflow-wrap:anywhere}input{display:block;padding:12px;background:#222;color:white;border:1px solid #aaa}</style>
<script>""" + force + """</script><script src="/static/vendor/liquid-metal/liquid-metal.js"></script><script src="/static/js/app-background.js"></script>
<div class="app-background" id="background" data-mode="auth" aria-hidden="true"></div>
<main><h1>背景能力隔离验证</h1><p>仅测试生产背景资产，非正式业务页面。</p>
<nav><a href="/normal">正常</a><a href="/reduced">减少动态</a><a href="/fallback">无 WebGL</a></nav>
<label>输入不受背景影响<input id="input" autocomplete="off"></label>
<button id="pause">模拟失焦</button><button id="resume">模拟聚焦</button><button id="replace">连续重挂载 12 次</button><button id="dispose">销毁</button><button id="read">读取状态</button>
<output id="state" role="status"></output></main><script>
const root=document.getElementById('background');let handle=AppBackground.mount(root,{mode:'auth'});
function read(){document.getElementById('state').textContent=JSON.stringify({mode:'""" + mode + """',...root.dataset,canvas:root.querySelectorAll('canvas').length},null,2)}
document.getElementById('read').onclick=read;
document.getElementById('pause').onclick=()=>{window.dispatchEvent(new Event('blur'));read()};
document.getElementById('resume').onclick=()=>{window.dispatchEvent(new Event('focus'));read()};
document.getElementById('dispose').onclick=()=>{handle.destroy();read()};
document.getElementById('replace').onclick=async()=>{const button=document.getElementById('replace');button.disabled=true;for(let i=0;i<12;i++){handle.destroy();handle=AppBackground.mount(root,{mode:'auth'});await new Promise(resolve=>setTimeout(resolve,700))}button.disabled=false;root.dataset.replacements='12';read()};read();
</script></html>""").encode("utf-8")
            mime = "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    print(f"http://127.0.0.1:{server.server_port}/normal", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
