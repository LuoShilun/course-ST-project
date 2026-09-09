# -*- coding: utf-8 -*-
"""测试数据（图片/视频/非法文件）准备。

真实水下图像来自项目数据集 TrashImage-2 的测试集，保证推理结果非空，
使"检测结果与落库记录一致性"这类用例具有实际判别力。
"""
from __future__ import annotations
import io
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
    """幂等准备测试数据；已存在则不覆盖。"""
    if not IMAGE_PLAIN.exists():
        IMAGE_PLAIN.write_bytes(_plain_jpeg())
    if not NOT_IMAGE.exists():
        NOT_IMAGE.write_bytes(NOT_IMAGE_TEXT)
    if not VIDEO_SAMPLE.exists():
        _make_video(VIDEO_SAMPLE)


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
    return VIDEO_SAMPLE.read_bytes()
