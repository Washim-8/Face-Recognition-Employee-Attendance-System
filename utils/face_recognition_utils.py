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

def _hog_encode(image):
    """Try HOG face detection (upsample=1 then 2) and return first encoding, or None."""
    locs = face_recognition.face_locations(
        image, number_of_times_to_upsample=1, model='hog')
    if not locs:
        locs = face_recognition.face_locations(
            image, number_of_times_to_upsample=2, model='hog')
    if locs:
        encs = face_recognition.face_encodings(
            image, known_face_locations=locs, num_jitters=1)
        if encs:
            return encs[0]
    return None


def _haar_encode(image_path):
    """
    Fallback: use OpenCV Haar cascade to locate the face (more lenient than dlib HOG),
    then pass the bbox DIRECTLY to face_recognition.face_encodings() as
    known_face_locations — completely bypassing HOG detection.
    This works on virtually any lit frontal/slightly-angled face.
    """
    bgr = cv2.imread(image_path)
    if bgr is None:
        return None

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # Very permissive: scaleFactor=1.05, minNeighbors=2, small minSize
    faces = cascade.detectMultiScale(
        gray, scaleFactor=1.05, minNeighbors=2, minSize=(20, 20))

    if len(faces) == 0:
        # Try even more lenient
        faces = cascade.detectMultiScale(
            gray, scaleFactor=1.03, minNeighbors=1, minSize=(15, 15))

    if len(faces) == 0:
        return None

    # Pick the largest face
    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
    x, y = max(0, x), max(0, y)
    x2 = min(bgr.shape[1], x + fw)
    y2 = min(bgr.shape[0], y + fh)

    # Convert to face_recognition format: (top, right, bottom, left)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    haar_loc = (y, x2, y2, x)

    # Try encoding at original size with known location
    encs = face_recognition.face_encodings(
        rgb, known_face_locations=[haar_loc], num_jitters=1)
    if encs:
        return encs[0]

    # Try at 2× upscale with scaled Haar location
    rgb2 = cv2.resize(rgb, (rgb.shape[1] * 2, rgb.shape[0] * 2),
                      interpolation=cv2.INTER_LINEAR)
    haar_loc2 = (y * 2, x2 * 2, y2 * 2, x * 2)
    encs2 = face_recognition.face_encodings(
        rgb2, known_face_locations=[haar_loc2], num_jitters=1)
    if encs2:
        return encs2[0]

    return None


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def load_image_and_encode(image_path):
    """
    Load an image from disk and return its 128-d face encoding, or None.

    IMPORTANT: Uses cv2.imread (not face_recognition.load_image_file) to avoid
    a PIL bug where some JPEGs are returned as RGBA 4-channel images, causing
    dlib to crash with "must be gray or RGB image".

    Tries 4 strategies, cheapest first:
      1. HOG on original RGB image
      2. HOG on 2x upscaled image
      3. HOG on 1.5x upscaled image
      4. Haar cascade → known_face_locations (bypasses HOG entirely)
    """
    try:
        # Load with OpenCV — always gives uint8 BGR, no alpha channel surprises
        bgr = cv2.imread(image_path)
        if bgr is None:
            print(f"  [SKIP] cv2 could not read: {os.path.basename(image_path)}")
            return None

        # Convert BGR → RGB (face_recognition/dlib expect RGB)
        image = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        # Ensure uint8 (dlib requirement)
        if image.dtype != np.uint8:
            image = image.astype(np.uint8)

        h, w = image.shape[:2]

        # Shrink very large images to prevent memory/speed issues
        if max(w, h) > 1200:
            scale = 1200.0 / max(w, h)
            image = cv2.resize(image, (int(w * scale), int(h * scale)),
                               interpolation=cv2.INTER_AREA)
            h, w = image.shape[:2]

        # Strategy 1 — HOG on original
        enc = _hog_encode(image)
        if enc is not None:
            return enc

        # Strategy 2 — HOG on 2x upscale
        enc = _hog_encode(cv2.resize(image, (w * 2, h * 2),
                                     interpolation=cv2.INTER_LINEAR))
        if enc is not None:
            return enc

        # Strategy 3 — HOG on 1.5x upscale
        enc = _hog_encode(cv2.resize(image, (int(w * 1.5), int(h * 1.5)),
                                     interpolation=cv2.INTER_LINEAR))
        if enc is not None:
            return enc

        # Strategy 4 — Haar → direct known_face_locations (bypasses HOG)
        enc = _haar_encode(image_path)
        if enc is not None:
            return enc

        print(f"  [FAIL] All 4 strategies failed: {os.path.basename(image_path)}")
        return None

    except Exception as e:
        print(f"  [ERR] {os.path.basename(image_path)}: {e}")
        return None




def encode_employee_from_dataset(employee_id):
    """
    Generate and store averaged face encoding for an employee
    from all captured dataset images.
    """
    emp_dir = os.path.join(config.DATASET_DIR, employee_id)
    if not os.path.exists(emp_dir):
        return False, "No dataset directory found for employee."

    image_files = sorted([f for f in os.listdir(emp_dir)
                          if f.lower().endswith(('.jpg', '.jpeg', '.png'))])

    if not image_files:
        return False, "No images found in dataset."

    print(f"[TRAIN] Processing {len(image_files)} images for employee '{employee_id}'...")

    all_encodings = []
    failed = 0
    for img_file in image_files:
        enc = load_image_and_encode(os.path.join(emp_dir, img_file))
        if enc is not None:
            all_encodings.append(enc)
        else:
            failed += 1

    print(f"   OK: {len(all_encodings)} encoded | FAIL: {failed} failed")

    if not all_encodings:
        return False, (
            f"No valid face encodings found in {len(image_files)} images. "
            "Please: Clear dataset → Re-capture with face front-on in good light → Train again."
        )

    avg_encoding = np.mean(all_encodings, axis=0)
    encoding_str = json.dumps(avg_encoding.tolist())

    if update_face_encoding(employee_id, encoding_str):
        print(f"[OK] Encoding stored for '{employee_id}' ({len(all_encodings)}/{len(image_files)} images used)")
        return True, f"Face model trained with {len(all_encodings)}/{len(image_files)} images!"
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
