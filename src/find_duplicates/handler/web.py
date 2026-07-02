import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import socket

from .core import load_json_report, validate_selections, recycle_files

# 将存储静态网页模板的路径
TEMPLATE_PATH = Path(__file__).parent / "templates" / "index.html"
REPORT_FILE_PATH = None

class HandlerHTTPRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # 覆写，静默日志输出以使控制台清爽
        pass

    def do_GET(self):
        global REPORT_FILE_PATH
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if TEMPLATE_PATH.is_file():
                with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            else:
                self.wfile.write("<h1>Error: Frontend template index.html not found!</h1>".encode("utf-8"))
        elif self.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            try:
                summary, duplicates = load_json_report(Path(REPORT_FILE_PATH))
                # 丰富返回数据，携带每个文件的基本状态
                rich_duplicates = {}
                for hsh, paths in duplicates.items():
                    group_files = []
                    for p_str in paths:
                        p = Path(p_str)
                        exists = p.is_file()
                        size = p.stat().st_size if exists else 0
                        mtime = p.stat().st_mtime if exists else 0
                        group_files.append({
                            "path": p_str,
                            "exists": exists,
                            "size": size,
                            "mtime": mtime
                        })
                    rich_duplicates[hsh] = group_files
                
                response = {
                    "status": "success",
                    "summary": summary,
                    "duplicates": rich_duplicates
                }
            except Exception as e:
                response = {"status": "error", "message": str(e)}
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self):
        global REPORT_FILE_PATH
        if self.path == "/api/action":
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            try:
                payload = json.loads(body.decode("utf-8"))
                # payload format: {"actions": {"hash_val": {"keep": "path1", "trash": ["path2"]}}}
                # Wait, backend receives userSelections payload which matches:
                # {"actions": {"hash_val": {"keep": "path1", "trash": ["path2"]}}}
                actions = payload.get("actions", {})
                
                # 重新加载报告，得到原始组清单，进行安全交叉验证
                _, duplicates = load_json_report(Path(REPORT_FILE_PATH))
                
                all_keep = set()
                all_trash = set()
                for hsh, detail in actions.items():
                    # Handle keep being a string or list
                    keep_val = detail.get("keep", [])
                    if isinstance(keep_val, str):
                        all_keep.add(keep_val)
                    else:
                        all_keep.update(keep_val)
                        
                    trash_val = detail.get("trash", [])
                    all_trash.update(trash_val)
                
                # 交叉安全核验
                err = validate_selections(duplicates, all_keep, all_trash)
                if err:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": err}).encode("utf-8"))
                    return
                
                # 物理执行
                count, reclaimed_bytes = recycle_files(list(all_trash))
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "count": count,
                    "reclaimed_bytes": reclaimed_bytes
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        else:
            self.send_error(404, "Endpoint Not Found")

def run_web_handler(report_path: str, host: str, port: int) -> None:
    global REPORT_FILE_PATH
    REPORT_FILE_PATH = report_path
    
    server_address = (host, port)
    try:
        httpd = HTTPServer(server_address, HandlerHTTPRequestHandler)
    except socket.error as err:
        print(f"[错误] 绑定端口 {port} 失败: {err}", file=sys.stderr)
        sys.exit(1)
        
    url = f"http://{host}:{port}/"
    print("==================================================")
    print("启动 Web GUI 服务成功！")
    print(f"监听地址: {url}")
    print("按 Ctrl+C 可以退出服务")
    print("==================================================")
    
    # 自动打开浏览器
    webbrowser.open(url)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nWeb 服务已关闭。")
        sys.exit(0)
