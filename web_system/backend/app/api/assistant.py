from __future__ import annotations

from pathlib import Path

import json
import os
import time
import uuid
from datetime import datetime
import requests
from werkzeug.utils import secure_filename
from flask import Blueprint, Response, current_app, request, send_from_directory, jsonify, stream_with_context

from app.services.assistant_service import AssistantService
from app.utils.auth import get_current_user, roles_required
from app.utils.response import api_error, api_success

bp = Blueprint("assistant", __name__, url_prefix="/api/assistant")

KB_META_FILENAME = ".kb_meta.json"


def _knowledge_base_dir() -> Path:
    backend_dir = Path(__file__).resolve().parents[2]
    data_dir = backend_dir / "data" / "knowledge_base"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _metadata_path() -> Path:
    return _knowledge_base_dir() / KB_META_FILENAME


def _load_metadata() -> dict:
    meta_path = _metadata_path()
    if not meta_path.exists():
        return {}
    try:
        with meta_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_metadata(meta: dict) -> None:
    meta_path = _metadata_path()
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def _allocate_stored_name(original_name: str) -> str:
    original_path = Path(original_name)
    ext = original_path.suffix
    safe_stem = secure_filename(original_path.stem)
    if not safe_stem:
        safe_stem = f"document_{uuid.uuid4().hex[:8]}"

    candidate = f"{safe_stem}{ext}"
    kb_dir = _knowledge_base_dir()
    index = 1
    while (kb_dir / candidate).exists():
        candidate = f"{safe_stem}_{index}{ext}"
        index += 1
    return candidate


def _env_file_path() -> Path:
    return Path(__file__).resolve().parents[2] / ".env"


def _upsert_env_values(updates: dict[str, str]) -> None:
    env_path = _env_file_path()
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    else:
        lines = []

    found_keys: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            new_lines.append(line)
            continue

        key = line.split("=", 1)[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            found_keys.add(key)
        else:
            new_lines.append(line)

    for key, value in updates.items():
        if key not in found_keys:
            new_lines.append(f"{key}={value}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _normalized_chat_url(base_url: str) -> str:
    url = base_url.strip().rstrip("/")
    if url.endswith("/chat/completions"):
        return url
    return f"{url}/chat/completions"


def _test_llm_connection(api_key: str, base_url: str, model_name: str) -> tuple[bool, str, int]:
    if not api_key or not base_url or not model_name:
        return False, "请完整填写 API Key、Base URL 和 Model", 0

    url = _normalized_chat_url(base_url)
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "你是一个简洁的系统连通性测试助手。"},
            {"role": "user", "content": "请仅回复：连接成功"},
        ],
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    start = time.time()
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        latency_ms = int((time.time() - start) * 1000)
        if resp.status_code >= 400:
            return False, f"模型接口返回状态码 {resp.status_code}", latency_ms
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return False, "模型响应缺少 choices 字段", latency_ms
        return True, "连接成功", latency_ms
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        return False, f"连接失败: {e}", latency_ms


@bp.get("/config/llm")
@roles_required("admin")
def get_llm_config():
    return api_success(
        {
            "provider": str(current_app.config.get("LLM_PROVIDER", "qwen")),
            "baseUrl": str(current_app.config.get("QWEN_BASE_URL", "")),
            "apiKey": str(current_app.config.get("QWEN_API_KEY", "")),
            "modelName": str(current_app.config.get("QWEN_MODEL", "qwen-plus")),
        }
    )


@bp.post("/config/llm/test")
@roles_required("admin")
def test_llm_config():
    data = request.get_json(silent=True) or {}
    api_key = str(data.get("apiKey") or current_app.config.get("QWEN_API_KEY", "")).strip()
    base_url = str(data.get("baseUrl") or current_app.config.get("QWEN_BASE_URL", "")).strip()
    model_name = str(data.get("modelName") or current_app.config.get("QWEN_MODEL", "qwen-plus")).strip()

    ok, message, latency_ms = _test_llm_connection(api_key, base_url, model_name)
    if not ok:
        return api_error(message, code=5001, http_status=502)
    return api_success({"latency_ms": latency_ms}, message=message)


@bp.put("/config/llm")
@roles_required("admin")
def save_llm_config():
    data = request.get_json(silent=True) or {}
    provider = str(data.get("provider", "qwen")).strip() or "qwen"
    api_key = str(data.get("apiKey", "")).strip()
    base_url = str(data.get("baseUrl", "")).strip()
    model_name = str(data.get("modelName", "")).strip()

    if not api_key or not base_url or not model_name:
        return api_error("API Key、Base URL、Model Name 不能为空", code=4001)

    current_app.config["LLM_PROVIDER"] = provider
    current_app.config["QWEN_API_KEY"] = api_key
    current_app.config["QWEN_BASE_URL"] = base_url
    current_app.config["QWEN_MODEL"] = model_name

    _upsert_env_values(
        {
            "LLM_PROVIDER": provider,
            "QWEN_API_KEY": api_key,
            "QWEN_BASE_URL": base_url,
            "QWEN_MODEL": model_name,
        }
    )

    return api_success(message="配置已保存并写入 .env")

@bp.post("/knowledge/upload")
# @roles_required("admin")  # 临时注销强制鉴权排查跨域与令牌黑�?
def upload_knowledge_file():
    """上传本地知识库文件，供RAG查询"""
    if "file" not in request.files:
        return jsonify({"code": 400, "message": "没有找到上传的文件部分"}), 400

    file = request.files["file"]
    if file.filename == "":
        return api_error("没有选择文件", code=4001)

    original_name = file.filename
    stored_name = _allocate_stored_name(original_name)

    kb_dir = _knowledge_base_dir()
    file_path = kb_dir / stored_name
    file.save(str(file_path))

    meta = _load_metadata()
    meta[stored_name] = {
        "original_name": original_name,
        "uploaded_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    _save_metadata(meta)

    file_size = file_path.stat().st_size
    chunks = max(1, file_size // 1024 // 10)

    return api_success({
        "id": stored_name,
        "name": original_name,
        "filename": stored_name,
        "status": "indexed",
        "chunks": chunks,
    }, message="上传成功")

@bp.get("/knowledge/download/<string:file_id>")
# @roles_required("admin")  # 临时注销强制鉴权排查跨域与令牌黑�?
def download_knowledge_file(file_id: str):
    """文件下载路由"""
    kb_dir = _knowledge_base_dir()
    file_path = kb_dir / file_id

    if not file_path.exists() or not file_path.is_file():
        return api_error("该文献在资源库中不存在，或文件已损坏", code=404)

    meta = _load_metadata()
    download_name = meta.get(file_id, {}).get("original_name", file_id)
    return send_from_directory(str(kb_dir), file_id, as_attachment=True, download_name=download_name)


@bp.get("/knowledge/list")
def list_knowledge_files():
    kb_dir = _knowledge_base_dir()
    meta = _load_metadata()
    files_list = []
    for entry in kb_dir.iterdir():
        if not entry.is_file() or entry.name == KB_META_FILENAME:
            continue
        file_size = entry.stat().st_size
        chunks = max(1, file_size // 1024 // 10)
        info = meta.get(entry.name, {})
        files_list.append({
            "id": entry.name,
            "name": info.get("original_name", entry.name),
            "status": "indexed",
            "chunks": chunks,
            "ctime": entry.stat().st_ctime,
        })

    files_list.sort(key=lambda x: x["ctime"], reverse=True)
    for item in files_list:
        del item["ctime"]
    return api_success(files_list)


@bp.delete("/knowledge/<string:file_id>")
def delete_knowledge_file(file_id: str):
    kb_dir = _knowledge_base_dir()
    file_path = kb_dir / file_id
    if not file_path.exists() or not file_path.is_file():
        return api_error("文件不存在", code=404)

    file_path.unlink()
    meta = _load_metadata()
    if file_id in meta:
        del meta[file_id]
        _save_metadata(meta)

    return api_success(message="删除成功")

@bp.get("/sessions")
@roles_required("admin", "user")
def list_sessions():
    user = get_current_user()
    assert user is not None
    return api_success(AssistantService.list_sessions(user.id))


@bp.get("/sessions/<string:session_id>/messages")
@roles_required("admin", "user")
def list_session_messages(session_id: str):
    user = get_current_user()
    assert user is not None
    return api_success(AssistantService.list_messages(user.id, session_id))


@bp.delete("/sessions/<string:session_id>")
@roles_required("admin", "user")
def delete_session(session_id: str):
    user = get_current_user()
    assert user is not None

    deleted = AssistantService.delete_session(user.id, session_id)
    if not deleted:
        return api_error("会话不存在或无权限删除", code=404, http_status=404)
    return api_success(message="会话删除成功")


@bp.post("/chat")
@roles_required("admin", "user")
def chat():
    user = get_current_user()
    assert user is not None

    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    if not question:
        return api_error("问题不能为空", code=4001)

    session_id = str(data.get("session_id", "")).strip() or None

    result = AssistantService.chat(
        repo_root=Path(current_app.config["REPO_ROOT"]),
        user_id=user.id,
        question=question,
        session_id=session_id,
        qwen_api_key=str(current_app.config.get("QWEN_API_KEY", "")),
        qwen_base_url=str(current_app.config.get("QWEN_BASE_URL", "")),
        qwen_model=str(current_app.config.get("QWEN_MODEL", "qwen-plus")),
    )

    return api_success(result)


@bp.post("/chat/stream")
@roles_required("admin", "user")
def chat_stream():
    user = get_current_user()
    assert user is not None

    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    if not question:
        return api_error("问题不能为空", code=4001)

    session_id = str(data.get("session_id", "")).strip() or None

    session = AssistantService.prepare_chat(user_id=user.id, question=question, session_id=session_id)
    sources = AssistantService.build_sources(repo_root=Path(current_app.config["REPO_ROOT"]), question=question)

    qwen_api_key = str(current_app.config.get("QWEN_API_KEY", ""))
    qwen_base_url = str(current_app.config.get("QWEN_BASE_URL", ""))
    qwen_model = str(current_app.config.get("QWEN_MODEL", "qwen-plus"))

    def event_payload(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    @stream_with_context
    def generate():
        chunks: list[str] = []
        yield event_payload({"type": "start", "session_id": session.id})

        try:
            if qwen_api_key:
                stream_iter = AssistantService._ask_qwen_stream(
                    question=question,
                    context=sources,
                    api_key=qwen_api_key,
                    base_url=qwen_base_url,
                    model=qwen_model,
                )
            else:
                fallback = AssistantService._build_local_answer(question=question, sources=sources)
                stream_iter = AssistantService.build_stream_from_text(fallback)

            for chunk in stream_iter:
                if not chunk:
                    continue
                chunks.append(chunk)
                yield event_payload({"type": "delta", "content": chunk})
        except Exception:
            if not chunks:
                fallback = AssistantService._build_local_answer(question=question, sources=sources)
                for chunk in AssistantService.build_stream_from_text(fallback):
                    chunks.append(chunk)
                    yield event_payload({"type": "delta", "content": chunk})

        answer = "".join(chunks).strip()
        if not answer:
            answer = "抱歉，当前未生成有效回答，请稍后重试。"

        AssistantService.save_assistant_message(session_id=session.id, answer=answer, sources=sources)
        yield event_payload({"type": "done", "answer": answer, "sources": sources, "session_id": session.id})

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
