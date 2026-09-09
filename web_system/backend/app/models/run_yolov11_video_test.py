from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO


def build_args() -> argparse.Namespace:
    base_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Run YOLOv11 inference on a test video.")
    parser.add_argument(
        "--model",
        type=Path,
        default=base_dir / "yolov11n.pt",
        help="Path to YOLOv11 weights (.pt).",
    )
    parser.add_argument(
        "--video",
        type=Path,
        default=base_dir / "bali.mp4",
        help="Path to input video.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=base_dir / "predict_outputs",
        help="Directory for prediction artifacts.",
    )
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold.")
    parser.add_argument("--iou", type=float, default=0.45, help="IoU threshold.")
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Inference device, e.g. cpu, 0, cuda:0.",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="manythings_yolov11",
        help="Output run folder name.",
    )
    parser.add_argument(
        "--exist-ok",
        action="store_true",
        help="Allow using an existing output run folder.",
    )
    return parser.parse_args()


def main() -> None:
    args = build_args()

    model_path = args.model.resolve()
    video_path = args.video.resolve()
    output_dir = args.output_dir.resolve()

    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    model = YOLO(str(model_path))
    results = model.predict(
        source=str(video_path),
        conf=args.conf,
        iou=args.iou,
        device=args.device,
        save=True,
        project=str(output_dir),
        name=args.name,
        exist_ok=args.exist_ok,
        verbose=True,
    )

    run_dir = output_dir / args.name
    print(f"Inference finished. Frames processed: {len(results)}")
    print(f"Artifacts saved to: {run_dir}")


if __name__ == "__main__":
    main()
