import cv2
import numpy as np
import os
import sys

# Global variable to hold the detector instance in worker processes
_worker_detector = None


def init_worker():
    """
    Initializes the PersonDetector in the worker process.
    """
    global _worker_detector
    _worker_detector = PersonDetector()


def process_file(filepath):
    """
    Process a single file using the worker's detector instance.
    Returns (filepath, has_people).
    """
    if _worker_detector is None:
        raise RuntimeError("Worker detector not initialized")

    return filepath, _worker_detector.contains_people(filepath)


class PersonDetector:
    def __init__(self):
        # Define paths to model files
        # We need to handle both development mode and PyInstaller frozen mode
        if getattr(sys, "frozen", False):
            # If running as a PyInstaller bundle
            base_dir = sys._MEIPASS
        else:
            # If running in normal python
            base_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )

        weights_path = os.path.join(base_dir, "models", "yolov3-tiny.weights")
        cfg_path = os.path.join(base_dir, "models", "yolov3-tiny.cfg")

        if not os.path.exists(weights_path) or not os.path.exists(cfg_path):
            raise FileNotFoundError(
                f"Model files not found at {weights_path} or {cfg_path}"
            )

        self.net = cv2.dnn.readNetFromDarknet(cfg_path, weights_path)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        layer_names = self.net.getLayerNames()
        self.output_layers = [
            layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()
        ]

    def contains_people(self, image_path):
        """
        Returns True if the image likely contains a person using YOLOv3-tiny.
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                return False

            height, width = img.shape[:2]

            # Create a blob
            # 1/255.0 scaling, 416x416 size, swapRB=True (BGR->RGB), crop=False
            blob = cv2.dnn.blobFromImage(
                img, 0.00392, (416, 416), (0, 0, 0), True, crop=False
            )
            self.net.setInput(blob)

            outs = self.net.forward(self.output_layers)

            # Scan through all the bounding boxes output from the network and keep only the
            # ones with high confidence scores. Assign the box's class label as the class with the highest score.
            for out in outs:
                for detection in out:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]

                    # Person is class 0
                    if class_id == 0 and confidence > 0.5:
                        return True

            return False
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            return False
