try:
    import face_recognition
except ImportError:
    import dlib
    import face_recognition_models

    class _FaceRecognitionFallback:
        """Lightweight drop-in replacement when face_recognition is not installed directly."""
        def __init__(self):
            self._detector = dlib.get_frontal_face_detector()
            self._predictor_68 = dlib.shape_predictor(
                face_recognition_models.pose_predictor_model_location()
            )
            self._predictor_5 = dlib.shape_predictor(
                face_recognition_models.pose_predictor_five_point_model_location()
            )
            self._encoder = dlib.face_recognition_model_v1(
                face_recognition_models.face_recognition_model_location()
            )

        def _css_to_rect(self, css):
            return dlib.rectangle(int(css[3]), int(css[0]), int(css[1]), int(css[2]))

        def _rect_to_css(self, rect):
            return rect.top(), rect.right(), rect.bottom(), rect.left()

        def face_locations(self, img, number_of_times_to_upsample=1, model='hog'):
            rects = self._detector(img, number_of_times_to_upsample)
            return [self._rect_to_css(r) for r in rects]

        def face_encodings(self, face_image, known_face_locations=None, num_jitters=1, model='small'):
            if known_face_locations is None:
                locations = self.face_locations(face_image)
            else:
                locations = known_face_locations

            rects = [self._css_to_rect(loc) for loc in locations]
            predictor = self._predictor_68 if model == 'large' else self._predictor_5
            raw_landmarks = [predictor(face_image, r) for r in rects]
            return [np.array(self._encoder.compute_face_descriptor(face_image, l, num_jitters)) for l in raw_landmarks]

        def face_distance(self, face_encodings, face_to_compare):
            if len(face_encodings) == 0:
                return np.empty((0))
            return np.linalg.norm(np.array(face_encodings) - np.array(face_to_compare), axis=1)

        def compare_faces(self, known_face_encodings, face_encoding_to_check, tolerance=0.6):
            return list(self.face_distance(known_face_encodings, face_encoding_to_check) <= tolerance)

        def load_image_file(self, file, mode='RGB'):
            im = cv2.imread(file)
            if im is None:
                raise ValueError(f"Could not load image: {file}")
            return cv2.cvtColor(im, cv2.COLOR_BGR2RGB)

    face_recognition = _FaceRecognitionFallback()

import numpy as np
import pickle
import json
import os
import sys
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.db_manager import get_all_face_encodings, update_face_encoding


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _haar_encode(bgr_image):
    """
    Fast face detector using OpenCV Haar cascade (runs in ~2-4ms).
    Passes detected face bounding box directly to dlib face_encodings,
    bypassing the slow whole-image HOG sliding window search.
    """
    try:
        gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        faces = cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=4, minSize=(50, 50))

        if len(faces) == 0:
            faces = cascade.detectMultiScale(
                gray, scaleFactor=1.05, minNeighbors=2, minSize=(30, 30))

        if len(faces) == 0:
            return None

        # Pick largest face
        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])

        # Add slight 8% margin for dlib facial landmark predictor
        pad_x = int(fw * 0.08)
        pad_y = int(fh * 0.08)
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(bgr_image.shape[1], x + fw + pad_x)
        y2 = min(bgr_image.shape[0], y + fh + pad_y)

        rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        haar_loc = (y1, x2, y2, x1)

        encs = face_recognition.face_encodings(
            rgb, known_face_locations=[haar_loc], num_jitters=1)
        if encs:
            return encs[0]
    except Exception:
        pass
    return None


def _hog_encode(rgb_image):
    """Fallback HOG face detection (upsample=0 then 1)."""
    try:
        locs = face_recognition.face_locations(
            rgb_image, number_of_times_to_upsample=0, model='hog')
        if not locs:
            locs = face_recognition.face_locations(
                rgb_image, number_of_times_to_upsample=1, model='hog')
        if locs:
            encs = face_recognition.face_encodings(
                rgb_image, known_face_locations=locs, num_jitters=1)
            if encs:
                return encs[0]
    except Exception:
        pass
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def load_image_and_encode(image_path):
    """
    Load an image from disk and return its 128-d face encoding, or None.
    Fast execution: uses OpenCV Haar pre-localization (~5ms) with HOG fallback.
    """
    try:
        bgr = cv2.imread(image_path)
        if bgr is None:
            return None

        h, w = bgr.shape[:2]
        # Standardize resolution for speed
        if max(w, h) > 800:
            scale = 800.0 / max(w, h)
            bgr = cv2.resize(bgr, (int(w * scale), int(h * scale)),
                             interpolation=cv2.INTER_AREA)

        # 1. Fast Haar Cascade detection + dlib encoding (~20ms)
        enc = _haar_encode(bgr)
        if enc is not None:
            return enc

        # 2. Fallback: HOG detection on RGB
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        enc = _hog_encode(rgb)
        if enc is not None:
            return enc

        return None
    except Exception as e:
        print(f"  [ERR] {os.path.basename(image_path)}: {e}")
        return None


def encode_employee_from_dataset(employee_id):
    """
    Generate and store averaged face encoding for an employee
    from captured dataset images with fast processing and early convergence.
    """
    emp_dir = os.path.join(config.DATASET_DIR, employee_id)
    if not os.path.exists(emp_dir):
        return False, "No dataset directory found for employee."

    image_files = sorted([f for f in os.listdir(emp_dir)
                          if f.lower().endswith(('.jpg', '.jpeg', '.png'))])

    if not image_files:
        return False, "No images found in dataset."

    print(f"[TRAIN] Processing images for employee '{employee_id}'...")

    all_encodings = []
    # 8 high-quality encodings are optimal for mean vector convergence
    target_encodings = min(len(image_files), 8)

    for img_file in image_files:
        enc = load_image_and_encode(os.path.join(emp_dir, img_file))
        if enc is not None:
            all_encodings.append(enc)
            if len(all_encodings) >= target_encodings:
                break  # Sufficient encodings collected, stop early for instant response

    if not all_encodings:
        return False, (
            f"No valid face encodings found in {len(image_files)} images. "
            "Please: Clear dataset → Re-capture with face front-on in good light → Train again."
        )

    avg_encoding = np.mean(all_encodings, axis=0)
    encoding_str = json.dumps(avg_encoding.tolist())

    if update_face_encoding(employee_id, encoding_str):
        print(f"[OK] Encoding stored for '{employee_id}' ({len(all_encodings)} images used)")
        return True, f"Face model trained successfully with {len(all_encodings)} images!"
    else:
        return False, "Failed to save encoding to database."


def load_known_encodings():
    """Load all known face encodings from DB. Returns (encodings, ids, names)."""
    employees = get_all_face_encodings()
    known_encodings, known_ids, known_names = [], [], []
    for emp in employees:
        if emp['face_encoding']:
            try:
                encoding = np.array(json.loads(emp['face_encoding']))
                known_encodings.append(encoding)
                known_ids.append(emp['employee_id'])
                known_names.append(emp['name'])
            except Exception as e:
                print(f"Error loading encoding for {emp['employee_id']}: {e}")
    return known_encodings, known_ids, known_names


def recognize_face_from_frame(frame_rgb, known_encodings, known_ids, known_names):
    """
    Detect and recognize faces in an RGB video frame.
    Returns list of result dicts with employee_id, name, location, confidence.
    """
    results = []
    if not known_encodings:
        return results

    # Downsample 2× for faster HOG detection
    small_frame = np.array(frame_rgb[::2, ::2])
    face_locations = face_recognition.face_locations(small_frame, model='hog')
    if not face_locations:
        return results

    face_encodings = face_recognition.face_encodings(small_frame, face_locations)

    for face_encoding, face_location in zip(face_encodings, face_locations):
        distances = face_recognition.face_distance(known_encodings, face_encoding)
        if len(distances) == 0:
            continue

        best_idx = int(np.argmin(distances))
        best_dist = distances[best_idx]
        top, right, bottom, left = [c * 2 for c in face_location]

        if best_dist <= config.FACE_RECOGNITION_TOLERANCE:
            results.append({
                'employee_id': known_ids[best_idx],
                'name': known_names[best_idx],
                'location': (top, right, bottom, left),
                'confidence': round((1 - best_dist) * 100, 1),
                'recognized': True
            })
        else:
            results.append({
                'employee_id': None,
                'name': 'Unknown',
                'location': (top, right, bottom, left),
                'confidence': 0,
                'recognized': False
            })

    return results


def encode_face_from_image_bytes(image_bytes):
    """Encode a face from raw image bytes. Returns encoding array or None."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        return None
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb_frame)
    return encodings[0] if encodings else None


def save_face_model():
    """Serialize all known encodings to a pickle backup file."""
    known_encodings, known_ids, known_names = load_known_encodings()
    os.makedirs(config.MODELS_DIR, exist_ok=True)
    with open(config.FACE_MODEL_PATH, 'wb') as f:
        pickle.dump({'encodings': known_encodings,
                     'ids': known_ids,
                     'names': known_names}, f)
    print(f"[OK] Face model saved with {len(known_ids)} employees.")
    return len(known_ids)


def match_face_from_encoding(face_encoding_array, known_encodings, known_ids, known_names):
    """Compare a single face encoding against known encodings. Returns (id, name, confidence)."""
    if not known_encodings or face_encoding_array is None:
        return None, None, 0
    distances = face_recognition.face_distance(known_encodings, face_encoding_array)
    best_idx = int(np.argmin(distances))
    best_dist = distances[best_idx]
    if best_dist <= config.FACE_RECOGNITION_TOLERANCE:
        return known_ids[best_idx], known_names[best_idx], round((1 - best_dist) * 100, 1)
    return None, None, 0
