#!/usr/bin/env python3
"""Interfaz local del Copiloto de Modernizacion. Uso: python app.py  (abre http://127.0.0.1:8765)"""
import json, os, sys, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pipeline import Run, listar_corridas, reconstruir_estado  # noqa: E402

CURRENT = {"run": None}
LOCK = threading.Lock()
MODELS = ["claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-2", "claude-haiku-5-5"]


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        r = CURRENT["run"]
        if u.path == "/":
            return self.send(200, open(os.path.join(HERE, "ui", "index.html"), encoding="utf-8").read(), "text/html; charset=utf-8")
        if u.path == "/api/config":
            return self.send(200, {"models": MODELS, "env_key": bool(os.environ.get("ANTHROPIC_API_KEY"))})
        if u.path == "/api/runs":
            return self.send(200, listar_corridas(HERE))
        if u.path == "/api/state":
            if not r:
                return self.send(200, {"status": "idle"})
            return self.send(200, r.snapshot(int(parse_qs(u.query).get("since", ["0"])[0])))
        if u.path in ("/api/download/zip", "/api/download/report", "/api/report") and r:
            nombre = "modern_loan.zip" if u.path.endswith("zip") else "informe_verificacion.md"
            f = r.p("salida", nombre)
            if os.path.exists(f):
                data = open(f, "rb").read()
                if u.path == "/api/report":
                    return self.send(200, data, "text/plain; charset=utf-8")
                return self.send(200, data, "application/zip" if nombre.endswith("zip") else "text/markdown; charset=utf-8",
                                 {"Content-Disposition": f'attachment; filename="{nombre}"'})
        self.send(404, {"error": "no encontrado"})

    def do_POST(self):
        if self.path not in ("/api/run", "/api/resume"):
            return self.send(404, {"error": "no encontrado"})
        n = int(self.headers.get("Content-Length", 0))
        d = json.loads(self.rfile.read(n) or b"{}")
        key = d.get("api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            return self.send(400, {"error": "Falta la clave de API de Anthropic."})
        if self.path == "/api/resume":
            rid = os.path.basename(str(d.get("run_id", "")))
            carpeta = os.path.join(HERE, "runs", rid)
            if not os.path.exists(os.path.join(carpeta, "estado.json")) and os.path.isdir(carpeta):
                reconstruir_estado(carpeta, rid)
            if not os.path.exists(os.path.join(carpeta, "estado.json")):
                return self.send(400, {"error": "No encuentro esa corrida en la carpeta runs."})
            with LOCK:
                if CURRENT["run"] and CURRENT["run"].state["status"] == "running":
                    return self.send(409, {"error": "Ya hay un flujo en ejecución."})
                run = Run(HERE, [], key, d.get("model") or MODELS[0], bool(d.get("segunda", True)), bool(d.get("web", False)), run_id=rid)
                try:
                    run.cargar(d.get("desde") or None)
                except (OSError, ValueError, KeyError) as e:
                    return self.send(400, {"error": f"No pude leer el estado de la corrida: {e}"})
                CURRENT["run"] = run
            threading.Thread(target=run.go, daemon=True).start()
            return self.send(200, {"run_id": run.id})
        if not d.get("files"):
            return self.send(400, {"error": "Sube al menos un archivo de código."})
        with LOCK:
            if CURRENT["run"] and CURRENT["run"].state["status"] == "running":
                return self.send(409, {"error": "Ya hay un flujo en ejecución."})
            run = Run(HERE, d["files"], key, d.get("model") or MODELS[0], bool(d.get("segunda", True)), bool(d.get("web", False)))
            CURRENT["run"] = run
        threading.Thread(target=run.go, daemon=True).start()
        self.send(200, {"run_id": run.id})


def main():
    faltan = []
    for m, pipname in (("pytest", "pytest"), ("yaml", "pyyaml")):
        try:
            __import__(m)
        except ImportError:
            faltan.append(pipname)
    if faltan:
        print("Faltan paquetes. Instálalos con:  pip install " + " ".join(faltan))
        sys.exit(1)
    port = int(os.environ.get("PORT", "8765"))
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    url = f"http://127.0.0.1:{port}"
    print(f"Copiloto de Modernización en {url}  (Ctrl+C para salir)")
    if not os.environ.get("NO_BROWSER"):
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
