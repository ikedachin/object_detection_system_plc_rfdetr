import datetime
from pathlib import Path

import numpy as np
from channels.db import database_sync_to_async
from PIL import Image, ImageDraw

from training.applications.rfdetr_native import detections_to_arrays


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
CLASS_COLOR_PALETTE = [
    (230, 57, 70),
    (29, 185, 84),
    (25, 130, 196),
    (255, 159, 28),
    (131, 56, 236),
    (0, 187, 249),
    (255, 214, 10),
    (67, 170, 139),
]


def _to_pil_image(img):
    if isinstance(img, Image.Image):
        return img.convert("RGB")
    if isinstance(img, np.ndarray):
        array = img
        if array.ndim == 3 and array.shape[2] == 3:
            # Camera frames are OpenCV BGR in this app.
            array = array[:, :, ::-1]
        return Image.fromarray(array).convert("RGB")
    return Image.open(img).convert("RGB")


def _label_name(detections, index, class_id, class_names):
    detection_names = getattr(detections, "data", {}).get("class_name")
    if detection_names is not None and index < len(detection_names) and detection_names[index]:
        return str(detection_names[index])
    class_id = int(class_id)
    if class_names and 0 <= class_id < len(class_names):
        return str(class_names[class_id])
    return str(class_id)


def _color_for_class_id(class_id):
    return CLASS_COLOR_PALETTE[int(class_id) % len(CLASS_COLOR_PALETTE)]


async def detect_objects(img: str | np.ndarray, model, project=None, training_run=None, **kwargs):
    save_folder_time = datetime.datetime.now().strftime("%H_%M_%S")
    save_folder_date = datetime.datetime.now().strftime("%Y%m%d")
    output_dir = BASE_DIR / "detect" / save_folder_date / save_folder_time
    result_image_path = output_dir / "predict" / "latest.png"
    result_image_path.parent.mkdir(parents=True, exist_ok=True)

    threshold = float(kwargs.get("conf", kwargs.get("threshold", 0.45)))
    class_names = kwargs.get("class_names") or []
    image = _to_pil_image(img)
    detections = model.predict(image, threshold=threshold)
    boxes, scores, labels = detections_to_arrays(detections)

    draw = ImageDraw.Draw(image)
    result_dict = {}
    detected_objects_info = []
    image_width, image_height = image.size

    for index, (box, score, label) in enumerate(zip(boxes, scores, labels)):
        class_id = int(label)
        class_name = _label_name(detections, index, class_id, class_names)
        result_dict[class_name] = result_dict.get(class_name, 0) + 1
        x0, y0, x1, y1 = [float(v) for v in box]
        x0 = max(0.0, min(float(image_width), x0))
        y0 = max(0.0, min(float(image_height), y0))
        x1 = max(0.0, min(float(image_width), x1))
        y1 = max(0.0, min(float(image_height), y1))
        width = max(0.0, x1 - x0)
        height = max(0.0, y1 - y0)
        color = _color_for_class_id(class_id)
        draw.rectangle([x0, y0, x1, y1], outline=color, width=3)
        draw.text((x0, y0), f"{class_name} {float(score):.2f}", fill=color)
        detected_objects_info.append({
            "class_id": class_id,
            "class_name": class_name,
            "confidence": float(score),
            "bbox_center_x": float((x0 + width / 2) / image_width) if image_width else 0.0,
            "bbox_center_y": float((y0 + height / 2) / image_height) if image_height else 0.0,
            "bbox_width": float(width / image_width) if image_width else 0.0,
            "bbox_height": float(height / image_height) if image_height else 0.0,
        })

    image.save(result_image_path)
    if project and training_run:
        await save_inference_result_to_db(
            detected_objects_info=detected_objects_info,
            detected_class_summary=result_dict,
            image_width=image_width,
            image_height=image_height,
            result_image_path=str(result_image_path),
            project=project,
            training_run=training_run,
            inference_config=kwargs,
        )
    return result_dict, np.asarray(image)


@database_sync_to_async
def save_inference_result_to_db(
    detected_objects_info,
    detected_class_summary,
    image_width,
    image_height,
    result_image_path,
    project,
    training_run,
    inference_config,
):
    from checker.models import DetectedObject, InferenceResult

    inference_result = InferenceResult.objects.create(
        project=project,
        training_run=training_run,
        model_name=training_run.model_name if hasattr(training_run, "model_name") else "Unknown",
        result_image_path=result_image_path,
        image_width=image_width,
        image_height=image_height,
        detected_class_summary=detected_class_summary,
        total_objects_count=len(detected_objects_info),
        inference_config=inference_config,
    )
    for obj_info in detected_objects_info:
        DetectedObject.objects.create(inference_result=inference_result, **obj_info)
    print(f"推論結果をデータベースに保存しました: {inference_result.id}")
    return inference_result
