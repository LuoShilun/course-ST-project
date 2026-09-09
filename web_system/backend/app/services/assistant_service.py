from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET

import requests

from app.extensions import db
from app.models import AssistantMessage, AssistantSession


class AssistantService:
    _knowledge_loaded = False
    _knowledge_lines: list[dict[str, str]] = []
    _knowledge_signature: str = ""

    @classmethod
    def chat(
        cls,
        repo_root: Path,
        user_id: int,
        question: str,
        session_id: str | None,
        qwen_api_key: str,
        qwen_base_url: str,
        qwen_model: str,
    ) -> dict[str, Any]:
        session = cls._get_or_create_session(user_id=user_id, session_id=session_id)

        user_msg = AssistantMessage(session_id=session.id, role="user", content=question, sources_json=[])
        db.session.add(user_msg)
        db.session.commit()

        sources = cls._search_local_knowledge(repo_root=repo_root, question=question)

        answer: str
        if qwen_api_key:
            try:
                answer = cls._ask_qwen(
                    question=question,
                    context=sources,
                    api_key=qwen_api_key,
                    base_url=qwen_base_url,
                    model=qwen_model,
                )
            except Exception:
                answer = cls._build_local_answer(question=question, sources=sources)
        else:
            answer = cls._build_local_answer(question=question, sources=sources)

        assistant_msg = AssistantMessage(
            session_id=session.id,
            role="assistant",
            content=answer,
            sources_json=sources,
        )
        db.session.add(assistant_msg)
        db.session.commit()

        return {
            "session_id": session.id,
            "answer": answer,
            "sources": sources,
            "messages": [user_msg.to_dict(), assistant_msg.to_dict()],
        }

    @staticmethod
    def prepare_chat(user_id: int, question: str, session_id: str | None) -> AssistantSession:
        session = AssistantService._get_or_create_session(user_id=user_id, session_id=session_id)
        user_msg = AssistantMessage(session_id=session.id, role="user", content=question, sources_json=[])
        db.session.add(user_msg)
        db.session.commit()
        return session

    @staticmethod
    def save_assistant_message(session_id: str, answer: str, sources: list[dict[str, str]]) -> AssistantMessage:
        assistant_msg = AssistantMessage(
            session_id=session_id,
            role="assistant",
            content=answer,
            sources_json=sources,
        )
        db.session.add(assistant_msg)
        db.session.commit()
        return assistant_msg

    @classmethod
    def build_sources(cls, repo_root: Path, question: str) -> list[dict[str, str]]:
        return cls._search_local_knowledge(repo_root=repo_root, question=question)

    @staticmethod
    def build_stream_from_text(text: str, chunk_size: int = 16) -> Iterable[str]:
        text = text or ""
        for i in range(0, len(text), chunk_size):
            yield text[i : i + chunk_size]

    @staticmethod
    def list_sessions(user_id: int) -> list[dict[str, Any]]:
        sessions = (
            AssistantSession.query.filter_by(user_id=user_id)
            .order_by(AssistantSession.updated_at.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sessions
        ]

    @staticmethod
    def list_messages(user_id: int, session_id: str) -> list[dict[str, Any]]:
        session = AssistantSession.query.filter_by(id=session_id, user_id=user_id).first()
        if session is None:
            return []
        messages = (
            AssistantMessage.query.filter_by(session_id=session_id)
            .order_by(AssistantMessage.created_at.asc())
            .all()
        )
        return [m.to_dict() for m in messages]

    @staticmethod
    def delete_session(user_id: int, session_id: str) -> bool:
        session = AssistantSession.query.filter_by(id=session_id, user_id=user_id).first()
        if session is None:
            return False

        db.session.delete(session)
        db.session.commit()
        return True

    @staticmethod
    def _get_or_create_session(user_id: int, session_id: str | None) -> AssistantSession:
        if session_id:
            session = AssistantSession.query.filter_by(id=session_id, user_id=user_id).first()
            if session is not None:
                return session

        session = AssistantSession(user_id=user_id, title="水下智能助手")
        db.session.add(session)
        db.session.commit()
        return session

    @classmethod
    def _search_local_knowledge(cls, repo_root: Path, question: str, top_k: int = 3) -> list[dict[str, str]]:
        cls._ensure_knowledge_loaded(repo_root)

        tokens = cls._tokenize(question)
        scored: list[tuple[int, dict[str, str]]] = []
        for item in cls._knowledge_lines:
            line_text = item["text"].lower()
            score = sum(1 for t in tokens if t and t in line_text)
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:top_k]]

    @classmethod
    def _ensure_knowledge_loaded(cls, repo_root: Path) -> None:
        kb_dir = repo_root / "web_system" / "backend" / "data" / "knowledge_base"
        signature = cls._build_knowledge_signature(kb_dir)

        if cls._knowledge_loaded and signature == cls._knowledge_signature:
            return

        lines = cls._load_uploaded_knowledge(kb_dir)
        if not lines:
            lines = cls._load_builtin_knowledge(repo_root)

        cls._knowledge_lines = lines
        cls._knowledge_loaded = True
        cls._knowledge_signature = signature

    @staticmethod
    def _build_knowledge_signature(kb_dir: Path) -> str:
        if not kb_dir.exists():
            return "missing"

        markers: list[str] = []
        for entry in kb_dir.iterdir():
            if entry.is_file():
                st = entry.stat()
                markers.append(f"{entry.name}:{int(st.st_mtime)}:{st.st_size}")
        markers.sort()
        return "|".join(markers)

    @classmethod
    def _load_uploaded_knowledge(cls, kb_dir: Path) -> list[dict[str, str]]:
        if not kb_dir.exists():
            return []

        meta_map: dict[str, Any] = {}
        meta_path = kb_dir / ".kb_meta.json"
        if meta_path.exists():
            try:
                meta_map = json.loads(meta_path.read_text(encoding="utf-8", errors="ignore"))
                if not isinstance(meta_map, dict):
                    meta_map = {}
            except Exception:
                meta_map = {}

        lines: list[dict[str, str]] = []
        for entry in kb_dir.iterdir():
            if not entry.is_file() or entry.name == ".kb_meta.json":
                continue

            display_name = str(meta_map.get(entry.name, {}).get("original_name", entry.name))
            text = cls._read_doc_text(entry)
            if not text:
                continue

            for chunk in cls._split_text_chunks(text):
                if len(chunk) < 20:
                    continue
                lines.append({"source": display_name, "text": chunk})

        return lines

    @classmethod
    def _load_builtin_knowledge(cls, repo_root: Path) -> list[dict[str, str]]:
        candidates = [
            repo_root / "MODEL_PIPELINE_CN.md",
            repo_root / "experiments" / "records" / "trash_icra19_dataset_report.md",
            repo_root / "experiments" / "records" / "thesis_extract_rxiaotian.txt",
        ]

        lines: list[dict[str, str]] = []
        for path in candidates:
            if not path.exists():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for row in text.splitlines():
                line = row.strip()
                if len(line) < 12:
                    continue
                lines.append({"source": str(path.relative_to(repo_root)).replace("\\", "/"), "text": line})
        return lines

    @staticmethod
    def _read_doc_text(path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md", ".csv", ".json", ".log", ".yaml", ".yml"}:
            return path.read_text(encoding="utf-8", errors="ignore")

        if suffix == ".docx":
            try:
                with zipfile.ZipFile(path) as zf:
                    xml_bytes = zf.read("word/document.xml")
                root = ET.fromstring(xml_bytes)
                text_nodes = [node.text for node in root.iter() if node.tag.endswith("}t") and node.text]
                return "\n".join(text_nodes)
            except Exception:
                return ""

        if suffix == ".pdf":
            try:
                from pypdf import PdfReader  # type: ignore

                reader = PdfReader(str(path))
                return "\n".join((p.extract_text() or "") for p in reader.pages)
            except Exception:
                return ""

        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    @staticmethod
    def _split_text_chunks(text: str, chunk_size: int = 380, overlap: int = 50) -> list[str]:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []

        chunks: list[str] = []
        start = 0
        length = len(normalized)
        while start < length:
            end = min(start + chunk_size, length)
            chunks.append(normalized[start:end])
            if end >= length:
                break
            start = max(end - overlap, start + 1)
        return chunks

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[A-Za-z0-9_\u4e00-\u9fff]{2,}", text.lower())

    @staticmethod
    def _build_local_answer(question: str, sources: list[dict[str, str]]) -> str:
        if not sources:
            return (
                "当前在本地项目文档中暂未找到直接证据。"
                "请补充更多上下文，例如模块名、页面名或目标接口。"
            )
        bullets = "\n".join([f"- {s['text']}" for s in sources])
        return (
            "基于本地项目知识，整理到以下相关要点：\n"
            f"{bullets}\n"
            "如果你愿意，我可以进一步整理为该系统可执行的分步操作。"
        )

    @staticmethod
    def _ask_qwen(question: str, context: list[dict[str, str]], api_key: str, base_url: str, model: str) -> str:
        context_text = "\n".join([f"[{c['source']}] {c['text']}" for c in context[:6]])
        url = base_url.rstrip("/")
        if not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions"

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是水下垃圾检测平台的智能助手，请严格依据给定本地知识片段回答，不确定时请明确说明。",
                },
                {
                    "role": "user",
                    "content": f"问题：{question}\n本地上下文：\n{context_text}",
                },
            ],
            "temperature": 0.3,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=40)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("Qwen 响应缺少 choices")
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            content = "".join([str(x.get("text", "")) for x in content if isinstance(x, dict)])
        if not content:
            raise RuntimeError("Qwen 响应内容为空")
        return content

    @staticmethod
    def _ask_qwen_stream(
        question: str,
        context: list[dict[str, str]],
        api_key: str,
        base_url: str,
        model: str,
    ) -> Iterable[str]:
        context_text = "\n".join([f"[{c['source']}] {c['text']}" for c in context[:6]])
        url = base_url.rstrip("/")
        if not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions"

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是水下垃圾检测平台的智能助手，请严格依据给定本地知识片段回答，不确定时请明确说明。",
                },
                {
                    "role": "user",
                    "content": f"问题：{question}\n本地上下文：\n{context_text}",
                },
            ],
            "temperature": 0.3,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        with requests.post(url, json=payload, headers=headers, timeout=60, stream=True) as resp:
            resp.raise_for_status()
            for raw_line in resp.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                line = str(raw_line).strip()
                if not line.startswith("data:"):
                    continue

                data_str = line[5:].strip()
                if not data_str or data_str == "[DONE]":
                    continue

                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                choices = data.get("choices", [])
                if not choices:
                    continue
                choice0 = choices[0] if isinstance(choices[0], dict) else {}

                delta = choice0.get("delta") if isinstance(choice0.get("delta"), dict) else {}
                chunk: str = ""
                content = delta.get("content")
                if isinstance(content, str):
                    chunk = content
                elif isinstance(content, list):
                    chunk = "".join(
                        str(x.get("text", ""))
                        for x in content
                        if isinstance(x, dict)
                    )

                if not chunk:
                    message = choice0.get("message") if isinstance(choice0.get("message"), dict) else {}
                    msg_content = message.get("content")
                    if isinstance(msg_content, str):
                        chunk = msg_content
                    elif isinstance(msg_content, list):
                        chunk = "".join(
                            str(x.get("text", ""))
                            for x in msg_content
                            if isinstance(x, dict)
                        )

                if chunk:
                    yield chunk
