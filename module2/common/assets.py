# -*- coding: utf-8 -*-
"""测试数据（图片/视频/非法文件）准备。

真实水下图像来自项目数据集 TrashImage-2 的测试集，保证推理结果非空，
使"检测结果与落库记录一致性"这类用例具有实际判别力。
"""
from __future__ import annotations
import io
import warnings
from pathlib import Path
from PIL import Image
from .paths import ASSETS_DIR

# 真实水下图像（含 Trash + Bio 目标）
IMAGE_WITH_TRASH = ASSETS_DIR / "underwater_trash_bio.jpg"
# 真实水下图像（仅 Bio 目标）
IMAGE_BIO_ONLY = ASSETS_DIR / "underwater_bio_only.jpg"
# 纯色合成图（无目标）
IMAGE_PLAIN = ASSETS_DIR / "plain_color.jpg"
# 非法内容
NOT_IMAGE = ASSETS_DIR / "not_an_image.txt"
# 视频
VIDEO_SAMPLE = ASSETS_DIR / "sample_clip.avi"

NOT_IMAGE_TEXT = b"this file is definitely not a decodable image payload.\n"


def _plain_jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (320, 240), (24, 96, 168)).save(buf, format="JPEG")
    return buf.getvalue()


def truncated_jpeg() -> bytes:
    """只保留前 96 字节的 JPEG，模拟传输中断/文件损坏。"""
    return _plain_jpeg()[:96]


def png_bytes(size=(256, 256), color=(10, 180, 90)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _make_video(path: Path, frames: int = 24, fps: float = 8.0) -> None:
    import cv2
    import numpy as np

    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (320, 240))
    for i in range(frames):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        frame[:, :] = (30 + i * 6 % 200, 90, 150)
        writer.write(frame)
    writer.release()


def ensure_assets() -> None:
    """幂等准备测试数据；已存在则不覆盖。

    任何一项准备失败都**不应中断整场测试**：生成视频依赖 cv2，而 cv2 可能未安装或
    已损坏（典型症状：anaconda 里 opencv-python 残留损坏时 ``import cv2`` 抛
    ``AttributeError: module 'cv2.dnn' has no attribute 'DictValue'``）。
    这里只对每一项做"尽力而为"的准备，失败时发 warning 并继续；真正需要该数据的
    用例会在读取时（如 ``video_bytes()``）得到明确报错，而不是把整个 pytest 会话打崩。
    """
    if not IMAGE_PLAIN.exists():
        try:
            IMAGE_PLAIN.write_bytes(_plain_jpeg())
        except Exception as exc:  # noqa: BLE001
            warnings.warn(f"[assets] 生成 plain_color.jpg 失败：{exc!r}")
    if not NOT_IMAGE.exists():
        NOT_IMAGE.write_bytes(NOT_IMAGE_TEXT)
    if not VIDEO_SAMPLE.exists():
        try:
            _make_video(VIDEO_SAMPLE)
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[assets] 生成 {VIDEO_SAMPLE.name} 失败（需要可用的 cv2）：{exc!r}。"
                f"可从 module1/assets/ 复制该文件，或修复本机 opencv-python 后重跑。"
            )


def image_bytes(name: str) -> bytes:
    ensure_assets()
    if name == "trash_bio":
        if IMAGE_WITH_TRASH.exists():
            return IMAGE_WITH_TRASH.read_bytes()
        return _plain_jpeg()
    if name == "bio_only":
        if IMAGE_BIO_ONLY.exists():
            return IMAGE_BIO_ONLY.read_bytes()
        return _plain_jpeg()
    if name == "plain":
        return _plain_jpeg()
    if name == "png":
        return png_bytes()
    if name == "truncated":
        return truncated_jpeg()
    if name == "not_image":
        return NOT_IMAGE_TEXT
    raise KeyError(name)


def video_bytes() -> bytes:
    ensure_assets()
    if not VIDEO_SAMPLE.exists():
        raise RuntimeError(
            f"缺少视频测试数据 {VIDEO_SAMPLE}，且本机无法用 cv2 生成。"
            "请从 module1/assets/ 复制 sample_clip.avi，或安装可用的 opencv-python。"
        )
    return VIDEO_SAMPLE.read_bytes()
