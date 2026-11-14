"""Prueba de integracion con un 'Claude de mentira': valida que las piezas encajan (no valida calidad del modelo)."""
import json, os, subprocess, sys, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
FIXT = os.path.join(HERE, "fixtures")  # datos de ejemplo incluidos en el repositorio
LEG = os.path.join(FIXT, "legacy")
FX = os.path.join(FIXT, "good")
RULES = os.path.join(LEG, "rules_final.json")

DEC = '''import json
d=json.load(open("extractor/auto/rules_autoaprobadas.json",encoding="utf-8"))
out=[]
for r in d["reglas"]:
    out.append({"rule_id":r["rule_id"],"decision":"aprobada","criterio":"codigo",
      "preguntas_cerradas":[{"pregunta":q,"respuesta":"Se mantiene como viene.","base":"tal_como_se_recibio"} for q in r.get("preguntas_abiertas",[])]})
json.dump({"decisiones":out},open("validador/decisiones.json","w",encoding="utf-8"),ensure_ascii=False)
'''
MK = f'''import shutil
shutil.copytree({FX!r}, "generador/modern_loan", dirs_exist_ok=True, ignore=shutil.ignore_patterns("rj.json","__pycache__"))
'''
MKV = '''import json
b="verificador/zip/modern_loan/"
json.dump({"interpretacion_legacy":["Pago posterior a las 20:00 pasa al dia siguiente."],
 "implementado_sin_regla":{"domain/rules.py::fee":{"clasificacion":"tecnico necesario","justificacion":"auxiliar"}},
 "observaciones":["prueba de flujo"]},open("verificador/narrativa.json","w",encoding="utf-8"),ensure_ascii=False)
json.dump({"escenarios":[{"id":"E1","regla":"R-013","entrada":{"hora":2001},"esperado":True,"fuente_esperado":"lectura_codigo","cita":"LNCALC01.cbl:1"},
 {"id":"E2","regla":"R-013","entrada":{"hora":2000},"esperado":False,"fuente_esperado":"lectura_codigo","cita":"LNCALC01.cbl:1"}]},open(b+"escenarios_equivalencia.json","w"))
open(b+"harness_equivalencia.py","w").write("import json,sys\\nfrom loan_calc.adapters.inbound.batch import run\\nes=json.load(open(sys.argv[1]))['escenarios']\\njson.dump({e['id']:run('LN-1',e['entrada']['hora']) for e in es},open(sys.argv[2],'w'))\\n")
'''


def tool(i, name, inp):
    return {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}],
            "usage": {"input_tokens": 10, "output_tokens": 5}}


def fin(t="listo"):
    return {"stop_reason": "end_turn", "content": [{"type": "text", "text": t}], "usage": {"input_tokens": 10, "output_tokens": 5}}


def respuesta(req):
    sysm = req["system"] if isinstance(req["system"], str) else req["system"][0]["text"]
    msgs = req["messages"]
    n = sum(1 for m in msgs if m["role"] == "assistant")
    first = msgs[0]["content"]
    if "# Extractor de reglas de negocio" in sysm:
        tag = "b" if "rules_b.json" in first else "a"
        if n == 0:
            return tool(n, "write_file", {"path": f"extractor/rules_{tag}.json", "content": open(RULES, encoding="utf-8").read()})
    elif "# Validador de reglas —" in sysm:
        if n == 0:
            return tool(n, "write_file", {"path": "validador/gen_dec.py", "content": DEC})
        if n == 1:
            return tool(n, "run_python", {"script": "validador/gen_dec.py"})
    elif "# Generador de código moderno desde" in sysm:
        if n == 0:
            return tool(n, "write_file", {"path": "generador/mk.py", "content": MK})
        if n == 1:
            return tool(n, "run_python", {"script": "generador/mk.py"})
    elif "# Verificador de equivalencia funcional" in sysm:
        if n == 0:
            return tool(n, "write_file", {"path": "verificador/mkv.py", "content": MKV})
        if n == 1:
            return tool(n, "run_python", {"script": "verificador/mkv.py"})
        if n == 2:
            return tool(n, "run_python", {"script": "tools/verificar.py", "args": [
                "verificador/zip", "--legacy", "input", "--narrativa", "verificador/narrativa.json", "--salida", "verificador/informe_verificacion.md"]})
    return fin()


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        for m in req["messages"]:
            if m["role"] == "assistant" and isinstance(m["content"], list):
                for b in m["content"]:
                    if b.get("type") == "thinking" and not (b.get("thinking") and b.get("signature")):
                        e = json.dumps({"type": "error", "error": {"type": "invalid_request_error", "message": "each thinking block must contain thinking"}}).encode()
                        self.send_response(400); self.send_header("Content-Length", str(len(e))); self.end_headers(); self.wfile.write(e); return
        r = respuesta(req)
        th = req.get("thinking")
        if th == {"type": "disabled"}:
            e = json.dumps({"type": "error", "error": {"type": "invalid_request_error", "message": 'To turn thinking off on this model, send "thinking": {"type": "between_tools"}'}}).encode()
            self.send_response(400); self.send_header("Content-Length", str(len(e))); self.end_headers(); self.wfile.write(e); return
        assert th == {"type": "between_tools"}, th
        assert req["system"][0]["cache_control"]
        r["content"] = [{"type": "thinking", "thinking": "aviso", "signature": "sig123"}] + r["content"]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        ev = lambda o: self.wfile.write(("event: x\ndata: " + json.dumps(o) + "\n\n").encode())
        ev({"type": "message_start", "message": {"usage": r.get("usage", {"input_tokens": 10})}})
        for i, b in enumerate(r["content"]):
            if b["type"] == "thinking":
                ev({"type": "content_block_start", "index": i, "content_block": {"type": "thinking", "thinking": ""}})
                ev({"type": "content_block_delta", "index": i, "delta": {"type": "thinking_delta", "thinking": b["thinking"]}})
                ev({"type": "content_block_delta", "index": i, "delta": {"type": "signature_delta", "signature": b["signature"]}})
            elif b["type"] == "text":
                ev({"type": "content_block_start", "index": i, "content_block": {"type": "text", "text": ""}})
                ev({"type": "content_block_delta", "index": i, "delta": {"type": "text_delta", "text": b["text"]}})
            else:
                ev({"type": "content_block_start", "index": i, "content_block": {**{k: v for k, v in b.items() if k != "input"}, "input": {}}})
                j = json.dumps(b["input"])
                ev({"type": "content_block_delta", "index": i, "delta": {"type": "input_json_delta", "partial_json": j[:5]}})
                ev({"type": "content_block_delta", "index": i, "delta": {"type": "input_json_delta", "partial_json": j[5:]}})
            ev({"type": "content_block_stop", "index": i})
        ev({"type": "message_delta", "delta": {"stop_reason": r.get("stop_reason", "end_turn")}, "usage": {"output_tokens": r.get("usage", {}).get("output_tokens", 5)}})
        ev({"type": "message_stop"})


def http(url, data=None):
    req = urllib.request.Request(url, json.dumps(data).encode() if data else None, {"content-type": "application/json"})
    return urllib.request.urlopen(req)


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", 8797), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    env = dict(os.environ, ANTHROPIC_BASE_URL="http://127.0.0.1:8797", NO_BROWSER="1", PORT="8798")
    app = subprocess.Popen([sys.executable, os.path.join(APP, "app.py")], env=env, cwd=APP, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(1.5)
    try:
        files = [{"name": n, "content": open(os.path.join(LEG, n), encoding="utf-8").read()} for n in ("LNCALC01.cbl", "PKG_LOAN_CALC.sql")]
        print("index:", len(http("http://127.0.0.1:8798/").read()), "bytes")
        print("run:", http("http://127.0.0.1:8798/api/run", {"files": files, "api_key": "test"}).read().decode())
        for _ in range(240):
            s = json.load(http("http://127.0.0.1:8798/api/state"))
            if s["status"] != "running":
                break
            time.sleep(1)
        print("status:", s["status"], "| error:", s.get("error"))
        for st in s["stages"]:
            print(f"  {st['status']:8} {st['name']}: {st['detail']} ({st['secs']}s)")
        print("verdict:", s.get("verdict"), "| tokens:", s["tokens"])
        for u in ("report", "zip"):
            print(u, len(http(f"http://127.0.0.1:8798/api/download/{u}").read()), "bytes")
        # ---- corrida antigua sin estado.json: se reconstruye desde los archivos
        rid = s["run_id"]
        est = os.path.join(APP, "runs", rid, "estado.json")
        import shutil
        os.remove(est)
        shutil.rmtree(os.path.join(APP, "runs", rid, "salida"))
        rec = [r for r in json.load(http("http://127.0.0.1:8798/api/runs")) if r["id"] == rid][0]
        print("reconstruida:", [(x["id"], x["status"]) for x in rec["stages"]])
        assert [x["status"] for x in rec["stages"]] == ["done", "done", "done", "pending", "pending"]
        # ---- reanudar: se simula una falla en la etapa 4 y se reanuda
        d = json.load(open(est))
        d["status"], d["error"] = "error", "falla simulada"
        for st in d["stages"][3:]:
            st.update(status="error" if st["id"] == "generate" else "pending", detail="falla simulada", secs=None)
        json.dump(d, open(est, "w"))
        lista = json.load(http("http://127.0.0.1:8798/api/runs"))
        print("corridas:", [(r["id"], r["listas"], r["total"]) for r in lista][:2])
        print("resume:", http("http://127.0.0.1:8798/api/resume", {"run_id": rid, "api_key": "test"}).read().decode())
        primero = json.load(http("http://127.0.0.1:8798/api/state"))
        print("al arrancar:", [(x["id"], x["status"]) for x in primero["stages"]])
        assert [x["status"] for x in primero["stages"]][:3] == ["done"] * 3
        for _ in range(240):
            s2 = json.load(http("http://127.0.0.1:8798/api/state"))
            if s2["status"] != "running":
                break
            time.sleep(1)
        print("reanudada:", s2["status"], [(x["id"], x["status"], x["secs"]) for x in s2["stages"]])
        assert s2["metrics"].get("reglas_extraidas") == 43
        assert any("Reanudación" in l for l in s2["log"]), "no hay marca de reanudación en el log"
        assert s2["outputs"].get("report") and s2["outputs"].get("zip")
        print("RESUME OK")
    finally:
        app.terminate()
