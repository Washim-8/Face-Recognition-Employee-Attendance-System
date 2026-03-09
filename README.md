<div align="center">

# 👤 AI-Powered Face Recognition Attendance System

<p align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&size=22&duration=3000&pause=1000&color=0F766E&center=true&vCenter=true&width=900&lines=Automated+Attendance+Using+Face+Recognition;Real-Time+Detection+with+OpenCV+%26+dlib;Full-Stack+Flask+Web+Application;Smart+Workforce+Management+System" alt="Typing SVG" />
</p>

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.3+-000000?style=for-the-badge&logo=flask&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

</div>

---

## 📌 Overview

This is a production-ready AI-powered attendance system that eliminates manual tracking by using real-time face recognition. Built with Flask and powered by computer vision, it provides instant employee check-in/check-out with a clean admin dashboard for workforce management.

The system solves the inefficiency of traditional attendance methods—no more paper registers, RFID cards, or manual entries. Just scan your face, and you're marked. It's fast, secure, and accurate, making it ideal for offices, schools, or any organization managing daily attendance.

---

## ✨ Features

### 🎯 Core Functionality
- **Real-time face recognition** using webcam
- **Instant attendance marking** (login/logout)
- **AI-powered face encoding** with dlib's 128-dimensional embeddings
- **Automated attendance recording** with timestamp tracking
- **Duplicate prevention** (can't check in twice on the same day)

### 🛠 Admin Dashboard
- **Live analytics** with attendance insights
- **Employee management** (add/edit/delete)
- **Attendance tracking** with date and employee filters
- **CSV export** for reports
- **Department-wise analytics** with visual charts
- **Late arrival detection** and working hours calculation

### 📷 Face Capture System
- **Auto-capture** multiple face samples (30 images)
- **Training progress tracking** with real-time feedback
- **One-click model training** with face encoding generation
- **Dataset management** (clear and recapture)

### 📈 Analytics & Reporting
- **Monthly attendance trends** (bar charts)
- **Weekly patterns** (line charts)
- **Department breakdown** (grouped bar charts)
- **Present vs Absent distribution** (doughnut charts)
- **Individual employee profiles** with attendance history

---

## 🛠 Tech Stack

**Backend:**
- Python 3.10+
- Flask (Web Framework)
- SQLite (Database)

**AI & Computer Vision:**
- face_recognition (Face detection & encoding)
- dlib (Face landmark detection)
- OpenCV (Image processing)
- NumPy (Numerical operations)

**Frontend:**
- HTML5, CSS3, JavaScript (Vanilla)
- Chart.js (Data visualization)
- Lucide Icons (UI icons)
- Inter & Outfit Fonts (Typography)

**Tools:**
- Git & GitHub (Version control)
- VS Code (Development)
- Pandas (Data export)

---

## 📂 Project Structure

```
face-recognition-attendance/
│
├── app.py                      # Main Flask application with all routes
├── config.py                   # Configuration (paths, tolerances, settings)
├── setup.py                    # Database initialization script
├── requirements.txt            # Python dependencies
│
├── utils/                      # Core business logic
│   ├── db_manager.py           # SQLite CRUD operations
│   ├── face_recognition_utils.py  # Face encoding & matching engine
│   ├── dataset_capture.py      # Webcam capture utilities
│   └── attendance_manager.py   # Attendance logic & analytics
│
├── templates/                  # Jinja2 HTML templates
│   ├── base.html               # Base template with navbar
│   ├── index.html              # Attendance terminal (main page)
│   ├── login.html              # Admin login
│   ├── admin_dashboard.html    # Dashboard with charts
│   ├── employees.html          # Employee list
│   ├── register_employee.html  # Add employee form
│   ├── edit_employee.html      # Edit employee form
│   ├── capture_face.html       # Face capture & training
│   ├── attendance.html         # Attendance records
│   ├── analytics.html          # Analytics page
│   ├── employee_profile.html   # Individual employee view
│   ├── about_contact.html      # Portfolio/About page
│   └── partials/sidebar.html   # Sidebar navigation
│
├── static/                     # Static assets
│   ├── css/style.css           # Complete design system
│   └── js/main.js              # JavaScript utilities
│
├── database/
│   ├── attendance.db           # SQLite database (auto-created)
│   └── database_schema.sql     # Schema reference
│
├── dataset/                    # Employee face images (auto-created)
│   ├── 1/                      # Employee ID folders
│   ├── 2/
│   └── ...
│
├── models/
│   └── face_model.pkl          # Serialized face encodings
│
└── reports/                    # Exported CSV reports
    └── attendance_report_*.csv
```

---

## ⚙️ How It Works

1. **Employee Registration**: Admin adds employee details through the web interface
2. **Face Capture**: System captures 30 face images via webcam for training
3. **Face Encoding**: AI generates 128-dimensional face embeddings using dlib
4. **Storage**: Encodings are stored in SQLite database for fast retrieval
5. **Recognition**: Employee scans face at terminal
6. **Matching**: System compares live face with stored encodings (Euclidean distance)
7. **Attendance Marking**: If match found (confidence > threshold), attendance is recorded
8. **Analytics**: Dashboard updates in real-time with attendance data

**Technical Details:**
- Uses dlib's ResNet-based face recognition model
- Face detection via HOG (Histogram of Oriented Gradients)
- 68-point facial landmark detection
- Tolerance threshold: 0.5 (configurable)
- Recognition speed: < 1 second per face

---

## ▶️ Installation & Setup

### Prerequisites
- Python 3.10 or higher
- Webcam (for face capture and recognition)
- Modern web browser (Chrome/Edge recommended)

### Step 1: Clone Repository
```bash
git clone https://github.com/Washim-8/face-recognition-attendance.git
cd face-recognition-attendance
```

### Step 2: Install Dependencies
```bash
pip install flask opencv-python face-recognition numpy pandas scikit-learn Pillow
```

**For Windows users (dlib fix):**
```bash
pip install "dlib @ https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.99-cp312-cp312-win_amd64.whl"
```

### Step 3: Initialize Database
```bash
python setup.py
```

### Step 4: Run Application
```bash
python app.py
```

### Step 5: Access Application
- **Main Terminal**: http://127.0.0.1:5000
- **Admin Panel**: http://127.0.0.1:5000/admin/login
- **Default Credentials**: `admin` / `admin123`

---

## 📸 Screenshots / Demo

### 🎥 Demo GIF Ideas
- Face scan → instant attendance marking
- Employee registration + face capture workflow
- Dashboard analytics auto-update
- CSV report export

**Tools for creating demos:**
- [ScreenToGif](https://www.screentogif.com/) (Windows)
- [OBS Studio](https://obsproject.com/) (Cross-platform)
- [Kap](https://getkap.co/) (macOS)

### 📷 Screenshot Suggestions
1. Attendance terminal with camera UI
2. Admin dashboard with live analytics
3. Face capture screen with progress
4. Employee management page
5. Analytics page with charts
6. Attendance records with filters

---

## 🔧 Configuration

Edit `config.py` to customize:

| Setting | Default | Description |
|---------|---------|-------------|
| `FACE_RECOGNITION_TOLERANCE` | `0.5` | Lower = stricter matching (0.4–0.6 recommended) |
| `IMAGES_PER_EMPLOYEE` | `30` | Number of face images to capture |
| `WORK_START_TIME` | `'09:00'` | Work start time for late detection |
| `LATE_THRESHOLD_MINUTES` | `15` | Grace period before marking late |
| `ADMIN_USERNAME` | `'admin'` | Default admin username |
| `ADMIN_PASSWORD` | `'admin123'` | Default admin password |

---

## 🗄 Database Schema

### `employees` Table
```sql
id, employee_id, name, department, email, phone, position, 
join_date, face_encoding, is_active
```

### `attendance` Table
```sql
id, employee_id, name, date, login_time, logout_time, 
working_hours, status, late_arrival
```

### `admin` Table
```sql
id, username, password, email, last_login
```

---

## 🚀 Future Improvements

- [ ] Deploy as cloud-based SaaS platform (AWS/Azure)
- [ ] Add mobile app integration (React Native/Flutter)
- [ ] Multi-face detection for group attendance
- [ ] Deep learning models for improved accuracy (FaceNet, ArcFace)
- [ ] Biometric + RFID hybrid system
- [ ] Real-time notifications (email/SMS alerts)
- [ ] Geofencing for location-based attendance
- [ ] Integration with HR management systems
- [ ] Advanced analytics with ML predictions
- [ ] Dark mode UI enhancement

---

## 🐛 Troubleshooting

**dlib installation fails on Windows:**
```bash
pip install "dlib @ https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.99-cp312-cp312-win_amd64.whl"
```

**Camera not accessible:**
- Allow camera permissions in browser settings
- Close other applications using the camera
- Use Chrome or Edge for best compatibility

**Face not recognized:**
- Ensure good lighting during capture and recognition
- Recapture face images with better quality
- Adjust `FACE_RECOGNITION_TOLERANCE` in config.py
- Capture at least 25-30 clear face images

**Database errors:**
```bash
python setup.py  # Reinitialize database
```

---

## 👨‍💻 About the Developer

I'm **Washim Shaikh**, a Computer Science student focused on building practical software that solves real problems. My work sits at the intersection of web development and artificial intelligence, where I create systems that make a tangible impact.

I've built platforms like **AgriTrade** that connect farmers directly with buyers, developed **AI chatbots** for intelligent conversations, and created **fraud detection systems** that protect financial transactions. My approach is simple: understand the problem, build a clean solution, and make it work reliably.

Currently, I'm expanding my expertise in AI systems and cloud architectures to build scalable, production-ready applications. I work with Python, Java, Django, and modern web technologies, with a strong focus on machine learning and data-driven solutions.

**Experience:**
- AI with Python Internship (Coincent)
- Machine Learning Internship (Yhills)
- Full Stack Development Internship (1Stop)
- AWS Internship (iStudio – ongoing)

**Skills:** Python, Java, Web Development (HTML/CSS/JS, Django), MySQL, Machine Learning, AI, Git, VS Code

---

## 📬 Contact

📧 **Email**: [washimshaikh33@gmail.com](mailto:washimshaikh33@gmail.com)  
📱 **Phone**: +91 8884958185  
💻 **GitHub**: [github.com/Washim-8](https://github.com/Washim-8)  
🔗 **LinkedIn**: [linkedin.com/in/washim-shaikh-349868281](https://www.linkedin.com/in/washim-shaikh-349868281/)

Feel free to connect for collaborations, opportunities, or just to discuss interesting projects.

---

## 📊 GitHub Stats

<p align="center">
  <img src="https://github-readme-stats.vercel.app/api?username=Washim-8&show_icons=true&theme=default&hide_border=true" alt="GitHub Stats" />
  <img src="https://github-readme-streak-stats.herokuapp.com/?user=Washim-8&theme=default&hide_border=true" alt="GitHub Streak" />
</p>

---

<div align="center">

### ⭐ Star this repository if you find it useful!

**Built with Python, Flask, and Computer Vision to modernize attendance systems through AI automation.**

</div>
