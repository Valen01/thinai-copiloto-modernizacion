"""Cliente minimo de la API de Claude con bucle de herramientas. Solo libreria estandar."""
import json, os, subprocess, sys, time, urllib.error, urllib.request

API_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com") + "/v1/messages"
MAX_OUT = 20000

TOOLS = [
    {"name": "list_files", "description": "Lista archivos del espacio de trabajo (rutas relativas). path puede ser una carpeta.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "read_file", "description": "Lee un archivo de texto. Usa start_line/end_line (1-based) para archivos largos.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "start_line": {"type": "integer"},
                                                        "end_line": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Crea o reemplaza un archivo de texto (crea carpetas). Contenido completo.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                      "required": ["path", "content"]}},
    {"name": "run_python", "description": "Ejecuta un script Python del espacio de trabajo (script) o pytest (module='pytest'). "
                                          "args = lista de argumentos. cwd relativo. pythonpath relativo (p. ej. 'generador/modern_loan/src').",
     "input_schema": {"type": "object", "properties": {"script": {"type": "string"}, "module": {"type": "string"},
                                                        "args": {"type": "array", "items": {"type": "string"}},
                                                        "cwd": {"type": "string"}, "pythonpath": {"type": "string"}}}},
]
WEB_SEARCH = {"type": "web_search_20250305", "name": "web_search", "max_uses": 8}


class AgentError(Exception):
    pass


_THINK = {"i": 0}
_THINK_OPCIONES = [{"type": "between_tools"}, None]  # None = no enviar el campo


def llm_call(key, model, system, messages, tools, log=None, progress=None):
    """Llama a la API con streaming: no hay silencios largos y se ve cuantos tokens genera el modelo."""
    # Cache de prompt: lo ya enviado se cobra a una fracción del precio en cada turno.
    sys_c = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    msgs = list(messages)
    if msgs:
        ult = dict(msgs[-1])
        cont = ult["content"]
        cont = [{"type": "text", "text": cont}] if isinstance(cont, str) else [dict(b) for b in cont]
        if cont:
            cont[-1]["cache_control"] = {"type": "ephemeral"}
        ult["content"] = cont
        msgs[-1] = ult
    cuerpo = {"model": model, "max_tokens": 32000, "system": sys_c, "messages": msgs, "tools": tools, "stream": True}
    for intento in range(6):
        c = dict(cuerpo)
        op = _THINK_OPCIONES[_THINK["i"]]
        if op:
            c["thinking"] = op
        req = urllib.request.Request(API_URL, json.dumps(c).encode(), {"content-type": "application/json", "x-api-key": key,
                                                                       "anthropic-version": "2023-06-01"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return _leer_stream(r, progress)
        except urllib.error.HTTPError as e:
            detalle = e.read().decode("utf-8", "replace")[:600]
            if e.code == 400 and "thinking" in detalle.lower() and _THINK["i"] < len(_THINK_OPCIONES) - 1 and "signature" not in detalle:
                _THINK["i"] += 1
                if log:
                    log("La API no aceptó el ajuste de razonamiento; se prueba otra configuración")
                continue
            if e.code in (429, 500, 502, 503, 529) and intento < 5:
                espera = int(e.headers.get("retry-after") or min(60, 5 * 2 ** intento)) if e.code == 429 else min(60, 5 * 2 ** intento)
                if log:
                    log(f"La API respondió {e.code} ({'límite de uso' if e.code == 429 else 'saturada'}); reintento en {espera} s ({intento + 1}/5)")
                time.sleep(espera)
                continue
            raise AgentError(f"API {e.code}: {detalle}")
        except (urllib.error.URLError, TimeoutError, ConnectionError, _StreamError) as e:
            if intento < 5:
                if log:
                    log(f"Conexión interrumpida ({type(e).__name__}); reintento ({intento + 1}/5)")
                time.sleep(min(60, 5 * 2 ** intento))
                continue
            raise AgentError(f"Sin conexion con la API: {e}")
    raise AgentError("La API no respondio")


class _StreamError(Exception):
    pass


def _leer_stream(r, progress):
    blocks, parcial, usage, stop = {}, {}, {"input_tokens": 0, "output_tokens": 0}, None
    for raw in r:
        linea = raw.decode("utf-8", "replace").strip()
        if not linea.startswith("data:"):
            continue
        try:
            ev = json.loads(linea[5:])
        except ValueError:
            continue
        t = ev.get("type")
        if t == "message_start":
            mu = ev["message"].get("usage", {})
            usage["input_tokens"] = mu.get("input_tokens", 0)
            usage["cache_read"] = mu.get("cache_read_input_tokens", 0)
            usage["cache_write"] = mu.get("cache_creation_input_tokens", 0)
        elif t == "content_block_start":
            blocks[ev["index"]] = dict(ev["content_block"])
            parcial[ev["index"]] = ""
        elif t == "content_block_delta":
            d, i = ev["delta"], ev["index"]
            if d.get("type") == "text_delta":
                blocks[i]["text"] = blocks[i].get("text", "") + d["text"]
            elif d.get("type") == "input_json_delta":
                parcial[i] += d.get("partial_json", "")
            elif d.get("type") == "thinking_delta":
                blocks[i]["thinking"] = blocks[i].get("thinking", "") + d.get("thinking", "")
            elif d.get("type") == "signature_delta":
                blocks[i]["signature"] = blocks[i].get("signature", "") + d.get("signature", "")
            if progress:
                progress(sum(len(b.get("text", "")) + len(b.get("thinking", "")) for b in blocks.values()) + sum(len(x) for x in parcial.values()))
        elif t == "content_block_stop":
            i = ev["index"]
            if blocks[i].get("type") in ("tool_use", "server_tool_use"):
                blocks[i]["input"] = json.loads(parcial[i]) if parcial[i].strip() else {}
        elif t == "message_delta":
            stop = ev["delta"].get("stop_reason", stop)
            usage["output_tokens"] = ev.get("usage", {}).get("output_tokens", usage["output_tokens"])
        elif t == "error":
            raise _StreamError(ev.get("error", {}).get("message", "error en el stream"))
    if stop is None:
        raise _StreamError("el stream terminó sin respuesta completa")
    return {"content": [blocks[i] for i in sorted(blocks)], "stop_reason": stop, "usage": usage}


class Session:
    def __init__(self, root, key, model, system, deny_read=(), web_search=False, log=None, usage=None, max_turns=80, activity=None):
        self.root, self.key, self.model, self.system = os.path.abspath(root), key, model, system
        self.deny = [d.replace("\\", "/").strip("/") for d in deny_read]
        self.tools = TOOLS + ([WEB_SEARCH] if web_search else [])
        self.log = log or (lambda m: None)
        self.usage = usage if usage is not None else {"in": 0, "out": 0}
        self.messages, self.max_turns = [], max_turns
        self.act = activity or (lambda m: None)

    # ---------- seguridad de rutas
    def safe(self, rel, leer=False):
        p = os.path.abspath(os.path.join(self.root, rel))
        if os.path.commonpath([p, self.root]) != self.root:
            raise AgentError("ruta fuera del espacio de trabajo")
        r = os.path.relpath(p, self.root).replace("\\", "/")
        if leer and any(r == d or r.startswith(d + "/") for d in self.deny):
            raise AgentError(f"acceso denegado a {r}: no forma parte de las entradas de este agente")
        return p

    # ---------- herramientas
    def t_list_files(self, path="."):
        p = self.safe(path)
        if os.path.isfile(p):
            return path
        out = []
        for r, ds, fs in os.walk(p):
            ds[:] = [d for d in ds if d not in ("__pycache__", ".git", ".pytest_cache")]
            for f in fs:
                rel = os.path.relpath(os.path.join(r, f), self.root).replace("\\", "/")
                if not any(rel == d or rel.startswith(d + "/") for d in self.deny):
                    out.append(rel)
        return "\n".join(sorted(out)[:400]) or "(vacio)"

    def t_read_file(self, path, start_line=None, end_line=None):
        with open(self.safe(path, True), encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        a, b = (start_line or 1), (end_line or len(lines))
        txt = "\n".join(lines[a - 1:b])
        return txt if len(txt) <= MAX_OUT else txt[:MAX_OUT] + f"\n[... recortado; usa start_line/end_line. Total {len(lines)} lineas]"

    def t_write_file(self, path, content):
        p = self.safe(path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        return f"escrito {path} ({len(content)} caracteres)"

    def t_run_python(self, script=None, module=None, args=None, cwd=".", pythonpath=None):
        args = [str(a) for a in (args or [])]
        if any(a == "-c" for a in args):
            raise AgentError("no se permite -c")
        argv = [sys.executable]
        if module:
            if module != "pytest":
                raise AgentError("solo se permite module='pytest'")
            argv += ["-m", "pytest", "-p", "no:cacheprovider"]
        elif script:
            p = self.safe(script, True)
            argv += (["-I"] if os.path.relpath(p, self.root).replace("\\", "/").startswith("tools/") else []) + [p]
        else:
            raise AgentError("indica script o module")
        env = dict(os.environ)
        if pythonpath:
            env["PYTHONPATH"] = os.pathsep.join(self.safe(x) for x in pythonpath.split(os.pathsep))
        cp = subprocess.run(argv + args, cwd=self.safe(cwd), env=env, capture_output=True, text=True, timeout=900)
        out = f"[exit {cp.returncode}]\n" + cp.stdout + cp.stderr
        return out if len(out) <= MAX_OUT else out[:MAX_OUT // 2] + "\n[...]\n" + out[-MAX_OUT // 2:]

    def ejecutar(self, nombre, entrada):
        try:
            return getattr(self, "t_" + nombre)(**entrada), False
        except AgentError as e:
            return f"ERROR: {e}", True
        except Exception as e:  # noqa
            return f"ERROR: {type(e).__name__}: {e}", True

    # ---------- bucle
    def compactar(self):
        """Si la conversación crece demasiado, la reinicia con un resumen: el trabajo vive en los archivos del espacio
        de trabajo. No se modifican mensajes viejos, porque la API firma el razonamiento sobre el contenido previo."""
        if sum(len(json.dumps(m)) for m in self.messages) < 450000:
            return
        textos = [m["content"] for m in self.messages if m["role"] == "user" and isinstance(m["content"], str)]
        nuevo = textos[0]
        if len(textos) > 1:
            nuevo += "\n\nÚltima indicación recibida:\n" + textos[-1]
        nuevo += ("\n\n[La conversación anterior se reinició por tamaño. Todo lo que ya hiciste está guardado en el espacio "
                  "de trabajo: revísalo con list_files y read_file, no lo rehagas y continúa donde quedaste.]")
        self.log("La conversación creció mucho; se reinicia con un resumen (el trabajo queda en los archivos)")
        self.messages = [{"role": "user", "content": nuevo}]

    def run(self, texto):
        self.messages.append({"role": "user", "content": texto})
        for _ in range(self.max_turns):
            self.compactar()
            self.act("Esperando al modelo…")
            r = llm_call(self.key, self.model, self.system, self.messages, self.tools, self.log,
                         lambda n: self.act(f"El modelo está escribiendo… (~{n // 4} tokens)"))
            u = r.get("usage", {})
            self.usage["in"] += u.get("input_tokens", 0)
            self.usage["out"] += u.get("output_tokens", 0)
            self.usage["cache"] = self.usage.get("cache", 0) + u.get("cache_read", 0)
            self.messages.append({"role": "assistant", "content": r["content"]})
            for b in r["content"]:
                if b.get("type") == "text" and b["text"].strip():
                    self.log(b["text"].strip()[:300])
            if r.get("stop_reason") == "tool_use":
                res = []
                for b in r["content"]:
                    if b.get("type") == "tool_use":
                        self.log(f"→ {b['name']} {json.dumps(b['input'], ensure_ascii=False)[:120]}")
                        self.act(f"Ejecutando {b['name']}…")
                        out, err = self.ejecutar(b["name"], b["input"])
                        res.append({"type": "tool_result", "tool_use_id": b["id"], "content": out, "is_error": err})
                self.messages.append({"role": "user", "content": res})
                continue
            if r.get("stop_reason") == "pause_turn":
                continue
            if r.get("stop_reason") == "max_tokens":
                aviso = ("Tu respuesta se cortó por el límite de longitud y esta herramienta NO se ejecutó. "
                         "Divide el trabajo: escribe archivos más pequeños (por ejemplo, las reglas en varios archivos "
                         "parciales de unas 10 reglas) y continúa.")
                self.log("La respuesta del modelo se cortó por longitud; se le pide dividir el trabajo")
                res = [{"type": "tool_result", "tool_use_id": b["id"], "content": aviso, "is_error": True}
                       for b in r["content"] if b.get("type") == "tool_use"]
                self.messages.append({"role": "user", "content": res + [{"type": "text", "text": aviso if not res else "Continúa."}]})
                continue
            return "\n".join(b["text"] for b in r["content"] if b.get("type") == "text")
        raise AgentError("el agente superó el máximo de pasos")
