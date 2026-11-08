"""The mock model: an HTTP server that serves the scripted work."""

import gzip
import json
import re
import socket
import threading
import time
import zlib
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from model.formats import STREAMS, completion, too_long
from model.requests import (
    CONTEXT_TOKENS,
    describe,
    history,
    is_compaction,
    is_side_request,
    request_details,
    results_of,
    strings,
    summary,
)
from workload import final_answer, steps


class Model:
    """Serves the work of one case to `agent`, at `rate` tokens per second."""

    def __init__(self, agent, rate, calls):
        self.agent, self.rate, self.calls = agent, rate, calls
        self.deltas = 0
        self.progress = {}
        self.request_sequence = 0
        self.previous = {}
        # The host directory that the agent sees as /workspace, and the tool that ran
        # each kind of call.
        self.workspace = None
        self.tools = {}
        self.verified_call = None
        self.shortened = set()
        # Calls whose result a compaction dropped before the model saw it.
        self.compacted = set()
        self.events = []
        self.auxiliary_events = []
        # Edits that the agent refused and the model sent again.
        self.retried_edits = 0
        # Every request by method and path, also those that are not inference.
        self.paths = Counter()
        self.error = None
        self.error_details = None
        self.lock = threading.Lock()
        self.ready = threading.Event()
        self.received = threading.Event()
        # The wall clock of the first request of the work.
        self.first_request = None
        self.ready.set()
        self.server = ThreadingHTTPServer(("0.0.0.0", 0), self.handler())
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def port(self):
        return self.server.server_port

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    def call(self, body, step):
        """The agent's tool call for `step`. Its tool must be on offer, and the
        call must fill every argument that the tool requires."""
        name, args = self.agent.call(step, body, self.workspace)
        offered = {
            tool.get("function", tool).get("name"): tool.get("function", tool)
            for tool in body.get("tools", [])
        }
        if name not in offered:
            raise ValueError(f"{name} is not on offer; offered: {sorted(offered)}")
        schema = offered[name].get("parameters", offered[name].get("input_schema", {}))
        if missing := set(schema.get("required", [])) - args.keys():
            raise ValueError(f"The call of {name} lacks {sorted(missing)}")
        return name, args

    def applied(self, step):
        """Whether the host sees the edit or write in the workspace."""
        path = self.workspace / step.path.removeprefix("/workspace/")
        text = path.read_text() if path.is_file() else ""
        if step.kind == "edit":
            return step.new in text and step.old not in text
        return text.rstrip() == step.output.rstrip()

    def asks_retry(self, body, call_id, step):
        """Whether the agent refused the edit of `call_id` and asks to retry it.
        The model retries an edit once."""
        return (
            step.kind == "edit"
            and not call_id.endswith("_retry")
            and any(
                mark in text
                for result in results_of(body, call_id)
                for text in strings(result)
                for mark in self.agent.edit_retries
            )
        )

    def verify_tool_result(self, body, call_id, step):
        returned = results_of(body, call_id)
        if not returned:
            return False
        content = "\n".join(strings(returned[0]))
        rows = step.output.rstrip().split("\n")
        if len(returned) != 1 or returned[0].get("is_error"):
            error = f"Missing or failed tool result {call_id}"
        elif step.kind in ("edit", "write"):
            if self.applied(step):
                self.verified_call = call_id
                return True
            error = f"The {step.kind} of {call_id} did not reach the file"
        elif rows[0] not in content:
            error = f"Incorrect fixture result {call_id}"
        else:
            # Agents can cut large results in history. The first row shows that the
            # call ran. A missing last row shows that the agent cut it.
            if rows[-1].strip() not in content:
                self.shortened.add(call_id)
            self.verified_call = call_id
            return True
        self.error_details = {
            "kind": step.kind,
            "expected_bytes": len(step.output or step.new),
            "returned_tool_result": returned,
        }
        raise ValueError(error)

    def handler(self):
        model = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def setup(self):
                super().setup()
                self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            def log_message(self, *_):
                pass

            def handle(self):
                try:
                    super().handle()
                except (ConnectionResetError, BrokenPipeError):
                    pass

            def json_response(self, value, status=200):
                body = json.dumps(value).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                with model.lock:
                    model.paths[f"GET {urlsplit(self.path).path}"] += 1
                self.json_response(
                    {
                        "object": "list",
                        "data": [
                            {
                                "id": "mock-model",
                                "object": "model",
                                "owned_by": "benchmark",
                            }
                        ],
                    }
                )

            def do_POST(self):
                try:
                    self.path = urlsplit(self.path).path
                    with model.lock:
                        model.paths[f"POST {self.path}"] += 1
                    length = int(self.headers.get("Content-Length", "0"))
                    if length > 64 * 1024 * 1024:
                        raise ValueError("Request exceeds 64 MiB")
                    data = self.rfile.read(length)
                    encoding = self.headers.get("Content-Encoding")
                    if encoding == "gzip":
                        data = gzip.decompress(data)
                    elif encoding == "deflate":
                        data = zlib.decompress(data)
                    body = json.loads(data)
                    tokens = len(data) // 4
                    if self.path.endswith("/count_tokens"):
                        self.json_response({"input_tokens": max(1, tokens)})
                        return
                    if tokens > CONTEXT_TOKENS:
                        with model.lock:
                            model.auxiliary_events.append(
                                {
                                    "kind": "rejected",
                                    "request_bytes": len(data),
                                    "verified_tool_call": None,
                                }
                            )
                        anthropic = self.path.endswith("/messages")
                        self.json_response(too_long(anthropic, tokens), 400)
                        return
                    with model.lock:
                        self.request_id = f"bench_{model.request_sequence:08d}"
                        model.request_sequence += 1
                    matches = [
                        int(m)
                        for s in strings(history(body))
                        for m in re.findall(r"BENCH_TURN_(\d{6})", s)
                    ]
                    compaction = is_compaction(body, model.agent)
                    if (
                        compaction
                        or is_side_request(body, model.agent)
                        or not body.get("tools")
                        or body.get("tool_choice") in ("none", {"type": "none"})
                    ):
                        # Tool results from several turns mean a summary prompt that
                        # the model does not know. It would get a generic answer,
                        # not the summary that the other agents get.
                        results = re.findall(r"fixture-(\d{6})-\d{3}", data.decode())
                        if not compaction and len(set(results)) > 1:
                            raise ValueError(
                                "Unrecognized auxiliary request carries tool results"
                                " of earlier turns"
                            )
                        with model.lock:
                            verified_call = None
                            if model.events:
                                pending = model.previous.get(model.events[-1]["turn"])
                                # A refused edit is not checked here. The next main
                                # request retries it.
                                if not pending or model.asks_retry(body, *pending):
                                    pass
                                elif model.verify_tool_result(body, *pending):
                                    verified_call = pending[0]
                                elif compaction:
                                    model.compacted.add(pending[0])
                            model.auxiliary_events.append(
                                {
                                    "kind": "compaction"
                                    if compaction
                                    else "generation",
                                    "request_bytes": len(data),
                                    "verified_tool_call": verified_call,
                                    **describe(self.path, body),
                                }
                            )
                        answer = "Fixture update completed."
                        if compaction and matches:
                            answer = summary(body, max(matches))
                        self.serve(body, "", answer, None, tokens)
                        return
                    if not matches:
                        raise ValueError(
                            "Unexpected auxiliary inference request without workload marker"
                        )
                    # Agents can put a compaction summary after the newest prompt.
                    turn = max(matches)
                    if model.first_request is None:
                        model.first_request = time.time()
                    model.received.set()
                    if not model.ready.wait(60):
                        raise TimeoutError("Host sampler did not become ready")
                    with model.lock:
                        index = model.progress.get(turn, 0)
                        if index > len(steps(turn, model.calls)):
                            model.error_details = request_details(body, turn, matches)
                            raise ValueError("Unexpected retry or extra model request")
                        retry = None
                        if index:
                            call_id, step = model.previous[turn]
                            if model.asks_retry(body, call_id, step):
                                retry = step
                            # Compaction can replace a result that the model checked in its
                            # input, or one that was dropped before the model saw it.
                            elif (
                                not model.verify_tool_result(body, call_id, step)
                                and model.verified_call != call_id
                                and call_id not in model.compacted
                            ):
                                model.error_details = request_details(
                                    body, turn, matches
                                )
                                raise ValueError(
                                    f"Missing or failed tool result {call_id}"
                                )
                        (thinking, answer), call = final_answer(turn), None
                        if retry:
                            thinking, answer = "", ""
                            name, args = model.call(body, retry)
                            call_id += "_retry"
                            call = (call_id, name, json.dumps(args))
                            model.previous[turn] = (call_id, retry)
                            model.retried_edits += 1
                        else:
                            if index < len(steps(turn, model.calls)):
                                step = steps(turn, model.calls)[index]
                                thinking, answer = step.thinking, step.answer
                                name, args = model.call(body, step)
                                model.tools.setdefault(step.kind, name)
                                call_id = f"call_bench_{turn:06d}_{index:03d}"
                                call = (call_id, name, json.dumps(args))
                                model.previous[turn] = (call_id, step)
                            model.progress[turn] = index + 1
                        event = {
                            "turn": turn,
                            "round": index,
                            "request_bytes": len(data),
                            "history_turns": sorted(set(matches)),
                        }
                        model.events.append(event)
                    self.serve(body, thinking, answer, call, tokens)
                except (BrokenPipeError, ConnectionResetError) as exc:
                    model.error = f"Agent disconnected: {type(exc).__name__}"
                except Exception as exc:  # noqa: BLE001 - report handler failures to runner
                    model.error = str(exc)
                    try:
                        self.json_response(
                            {
                                "error": {
                                    "message": model.error,
                                    "type": "benchmark_error",
                                }
                            },
                            400,
                        )
                    except OSError:
                        pass

            def serve(self, body, thinking, answer, call, input_tokens):
                anthropic = self.path.endswith("/messages")
                if not body.get("stream", True):
                    self.json_response(
                        completion(anthropic, body, answer, input_tokens)
                    )
                    return
                stream = next(
                    (f for suffix, f in STREAMS.items() if self.path.endswith(suffix)),
                    None,
                )
                if not stream:
                    raise ValueError(f"Unsupported endpoint {self.path}")
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True
                started, sent = time.monotonic(), 0
                events = stream(
                    body, self.request_id, thinking, answer, call, input_tokens
                )
                for event, value, paced in events:
                    if paced:
                        sent += len(paced)
                        with model.lock:
                            model.deltas += 1
                        if model.rate:
                            delay = started + sent / (4 * model.rate) - time.monotonic()
                            if delay > 0:
                                time.sleep(delay)
                    data = value if isinstance(value, str) else json.dumps(value)
                    prefix = f"event: {event}\n" if event else ""
                    self.wfile.write(f"{prefix}data: {data}\n\n".encode())
                    self.wfile.flush()

        return Handler
