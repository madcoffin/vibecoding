import os
import shutil
import threading
import queue
import json
import yt_dlp
from flask import Flask, render_template, request, jsonify, Response, stream_with_context

app = Flask(__name__)

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "Downloads")

_lock = threading.Lock()
_state = {
    "is_downloading": False,
    "cancel_flag":    False,
    "output_dir":     DEFAULT_DIR,
    "status":         "READY!",
    "progress":       0,
    "logs":           [],   # [{msg, tag}, ...]
}
_subscribers: list[queue.Queue] = []


# ── broadcast helpers ────────────────────────────────────────────────────────

def _broadcast(event_type: str, data):
    payload = json.dumps({"type": event_type, "data": data})
    with _lock:
        dead = []
        for q in _subscribers:
            try:
                q.put_nowait(payload)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _subscribers.remove(q)


def _send_log(msg: str, tag: str):
    with _lock:
        _state["logs"].append({"msg": msg, "tag": tag})
    _broadcast("log", {"msg": msg, "tag": tag})


def _send_status(status: str):
    with _lock:
        _state["status"] = status
    _broadcast("status", status)


def _send_progress(value: int):
    with _lock:
        _state["progress"] = value
    _broadcast("progress", value)


# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template(
        "index.html",
        ffmpeg_available=FFMPEG_AVAILABLE,
        default_dir=DEFAULT_DIR,
    )


@app.route("/state")
def get_state():
    with _lock:
        return jsonify({
            "is_downloading": _state["is_downloading"],
            "status":         _state["status"],
            "progress":       _state["progress"],
            "logs":           list(_state["logs"]),
            "output_dir":     _state["output_dir"],
        })


@app.route("/start", methods=["POST"])
def start_download():
    data       = request.get_json(silent=True) or {}
    url        = (data.get("url") or "").strip()
    output_dir = (data.get("output_dir") or "").strip()

    if not url:
        return jsonify({"error": "URL을 입력해주세요."}), 400

    with _lock:
        if _state["is_downloading"]:
            return jsonify({"error": "이미 다운로드 중입니다."}), 409
        _state["is_downloading"] = True
        _state["cancel_flag"]    = False
        _state["progress"]       = 0
        _state["logs"]           = []
        if output_dir:
            _state["output_dir"] = os.path.expanduser(output_dir)

    threading.Thread(target=_download_worker, args=(url,), daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/cancel", methods=["POST"])
def cancel_download():
    with _lock:
        _state["cancel_flag"] = True
    return jsonify({"status": "cancelling"})


@app.route("/stream")
def stream():
    q: queue.Queue = queue.Queue(maxsize=300)
    with _lock:
        _subscribers.append(q)
        snapshot = {
            "is_downloading": _state["is_downloading"],
            "status":         _state["status"],
            "progress":       _state["progress"],
            "logs":           list(_state["logs"]),
            "output_dir":     _state["output_dir"],
        }

    def generate():
        try:
            # Send current state immediately so the page can restore mid-download
            yield f"data: {json.dumps({'type': 'state', 'data': snapshot})}\n\n"
            while True:
                try:
                    payload = q.get(timeout=25)
                    yield f"data: {payload}\n\n"
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        finally:
            with _lock:
                if q in _subscribers:
                    _subscribers.remove(q)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── download worker ───────────────────────────────────────────────────────────

def _download_worker(url: str):
    try:
        _send_status("ᗧ···  재생목록 정보 로딩 중...")
        _send_log("ᗧ  재생목록 정보를 가져오는 중입니다...", "info")

        with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
            info = ydl.extract_info(url, download=False)

        if info is None:
            _send_log("ᗣ  URL에서 정보를 가져올 수 없습니다.", "error")
            return

        entries = info.get("entries") or [info]
        total   = len(entries)
        _send_log(f"· · ·  총 {total}개의 영상 발견  · · ·", "success")

        for idx, entry in enumerate(entries, start=1):
            with _lock:
                cancelled = _state["cancel_flag"]
            if cancelled:
                _send_log("ᗣ  GAME OVER — 다운로드가 취소되었습니다.", "error")
                break

            title     = entry.get("title", f"영상 {idx}")
            video_url = entry.get("url") or entry.get("webpage_url") or url

            _send_log(f"ᗧ  [{idx}/{total}]  {title}", "title")
            _send_status(f"ᗧ···  LEVEL {idx}/{total}  —  {title}")
            _send_progress(int((idx - 1) / total * 100))

            if FFMPEG_AVAILABLE:
                fmt            = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                postprocessors = [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}]
                merge_fmt      = "mp4"
            else:
                fmt            = "best[ext=mp4]/best"
                postprocessors = []
                merge_fmt      = None

            with _lock:
                output_dir = _state["output_dir"]

            ydl_opts = {
                "format":         fmt,
                "outtmpl":        os.path.join(output_dir, "%(title)s.%(ext)s"),
                "quiet":          True,
                "no_warnings":    True,
                "progress_hooks": [_make_hook(idx, total)],
                "postprocessors": postprocessors,
            }
            if merge_fmt:
                ydl_opts["merge_output_format"] = merge_fmt

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])
                _send_log(f"   ★ CLEAR!  {title}", "success")
            except Exception as e:
                _send_log(f"   ᗣ ERROR: {e}", "error")

        _send_progress(100)
        with _lock:
            cancelled  = _state["cancel_flag"]
            output_dir = _state["output_dir"]

        if not cancelled:
            _send_log("", "info")
            _send_log("ᗧ· · · · · · · · · · ·  ALL STAGES CLEAR!  · · · · · · · · · · ·ᗤ", "success")
            _send_log(f"저장 위치: {output_dir}", "info")
            _send_status("ᗧ  ALL CLEAR!  — 다운로드 완료")
        else:
            _send_status("ᗣ  GAME OVER")

    except Exception as e:
        _send_log(f"ᗣ  오류 발생: {e}", "error")
        _send_status("ᗣ  ERROR")
    finally:
        with _lock:
            _state["is_downloading"] = False
        _broadcast("done", {})


def _make_hook(idx: int, total: int):
    def hook(d):
        with _lock:
            cancelled = _state["cancel_flag"]
        if cancelled:
            raise Exception("사용자가 취소했습니다.")
        if d["status"] == "downloading":
            downloaded  = d.get("downloaded_bytes", 0)
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            if total_bytes:
                pct = ((idx - 1) + downloaded / total_bytes) / total * 100
                _send_progress(int(pct))
    return hook


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import webbrowser
    port = 5000
    print(f"\nᗧ···  PAC-MAN DOWNLOADER (Web)  —  http://localhost:{port}")
    print("Ctrl+C to stop\n")
    webbrowser.open(f"http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
