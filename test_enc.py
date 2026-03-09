import sys, os, cv2, numpy as np
sys.path.insert(0, '.')
import config, face_recognition

emp_dir = os.path.join(config.DATASET_DIR, '1')
p = os.path.join(emp_dir, sorted(os.listdir(emp_dir))[0])
print("Testing:", p)

bgr = cv2.imread(p)
rgb = face_recognition.load_image_file(p)
print("RGB shape:", rgb.shape, "dtype:", rgb.dtype)

gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
faces = cascade.detectMultiScale(gray, 1.05, 2, minSize=(20,20))
print("Haar faces:", len(faces))

if len(faces) > 0:
    x, y, fw, fh = faces[0]
    haar_loc = (y, x+fw, y+fh, x)
    print("haar_loc:", haar_loc)
    try:
        encs = face_recognition.face_encodings(rgb, known_face_locations=[haar_loc], num_jitters=1)
        print("ENCODING OK:", len(encs), "shape:", encs[0].shape if encs else None)
    except Exception as e:
        print("ENCODING ERROR:", type(e).__name__, str(e))
else:
    print("No Haar face detected - checking full image encoding...")
    try:
        encs = face_recognition.face_encodings(rgb)
        print("Direct encodings:", len(encs))
    except Exception as e:
        print("Direct encoding error:", type(e).__name__, str(e))
