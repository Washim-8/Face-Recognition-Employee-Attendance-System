import cv2
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def capture_face_dataset(employee_id, num_images=None):
    """
    Capture face images from webcam and save to dataset directory.
    This is a standalone script for capturing from a local webcam.
    
    Args:
        employee_id: The employee ID to create dataset for
        num_images: Number of images to capture (default from config)
    """
    if num_images is None:
        num_images = config.IMAGES_PER_EMPLOYEE
    
    # Create employee directory
    emp_dir = os.path.join(config.DATASET_DIR, employee_id)
    os.makedirs(emp_dir, exist_ok=True)
    
    # Load face detector
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Error: Cannot open camera.")
        return False
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    count = 0
    print(f"📸 Capturing {num_images} images for employee {employee_id}")
    print("Press 'q' to quit early, 's' to skip a frame.")
    
    while count < num_images:
        ret, frame = cap.read()
        if not ret:
            break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )
        
        display_frame = frame.copy()
        
        for (x, y, w, h) in faces:
            cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            if count < num_images:
                # Auto-capture with slight delay
                face_img = frame[y:y+h, x:x+w]
                img_path = os.path.join(emp_dir, f"face_{count+1:03d}.jpg")
                cv2.imwrite(img_path, face_img)
                count += 1
                time.sleep(0.1)
        
        # Add overlay info
        cv2.putText(display_frame, f"Captured: {count}/{num_images}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(display_frame, f"Employee: {employee_id}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        if len(faces) == 0:
            cv2.putText(display_frame, "No face detected - adjust position",
                        (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        progress_pct = int(count / num_images * 100)
        bar_width = int(display_frame.shape[1] * progress_pct / 100)
        cv2.rectangle(display_frame, (0, display_frame.shape[0]-10),
                      (bar_width, display_frame.shape[0]), (0, 255, 0), -1)
        
        cv2.imshow(f'Face Capture - Employee {employee_id}', display_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    print(f"✅ Captured {count} images for employee {employee_id}")
    return count > 0


def capture_frame_from_bytes(image_bytes):
    """
    Decode image bytes from web camera (base64 decoded) to OpenCV frame.
    Used for web-based face capture.
    """
    import numpy as np
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return frame


def save_captured_frame(employee_id, frame, frame_index):
    """
    Save a captured webcam frame for the employee dataset.
    Always saves the FULL FRAME so that face_recognition's dlib detector
    has enough context and resolution to encode the face correctly.
    Saving tight crops causes 'No valid face encodings found' because
    dlib's HOG detector needs surrounding context.
    """
    emp_dir = os.path.join(config.DATASET_DIR, employee_id)
    os.makedirs(emp_dir, exist_ok=True)

    img_path = os.path.join(emp_dir, f"face_{frame_index:03d}.jpg")

    # Quick pre-check: does a face exist in this frame? (don't save blank frames)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=4, minSize=(50, 50)
    )

    # Always save the FULL frame — face_recognition needs full resolution + context
    # A tight 100×100 crop will fail dlib's HOG face detector during encoding
    cv2.imwrite(img_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return len(faces) > 0  # Return whether a face was visually detected


def get_captured_count(employee_id):
    """Get the number of images captured for an employee."""
    emp_dir = os.path.join(config.DATASET_DIR, employee_id)
    if not os.path.exists(emp_dir):
        return 0
    return len([f for f in os.listdir(emp_dir)
                if f.lower().endswith(('.jpg', '.jpeg', '.png'))])


def clear_dataset(employee_id):
    """Clear all captured images for an employee."""
    emp_dir = os.path.join(config.DATASET_DIR, employee_id)
    if os.path.exists(emp_dir):
        import shutil
        shutil.rmtree(emp_dir)
        os.makedirs(emp_dir)
        return True
    return False


if __name__ == '__main__':
    if len(sys.argv) > 1:
        emp_id = sys.argv[1]
        capture_face_dataset(emp_id)
    else:
        print("Usage: python dataset_capture.py <employee_id>")
