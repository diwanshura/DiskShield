# 💾 DiskShield — Disk Space Monitor

A tool that monitors disk space and alerts users when it reaches a critical level.

A clean, real-time disk monitoring dashboard that alerts you within **3 seconds** when disk usage reaches warning or critical levels.

---

## 📁 Project Structure

```
diskwatch/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   └── diskwatch.db
└── frontend/
    └── index.html
```

---

## ⚡ Quick Start (5 Minutes)

### Step 1 — Set Up the Backend

```bash
cd diskwatch/backend
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

---

### Step 2 — Open the Frontend

Open:

```
diskwatch/frontend/index.html
```

---

## 🧪 Testing Alerts

1. Open dashboard
2. Set warning below current usage
3. Click **Set**
4. Alerts will appear within seconds

---

## 🔌 API Endpoints

| Method | Endpoint          | Description          |
| ------ | ----------------- | -------------------- |
| GET    | /api/disks        | Get all disks        |
| GET    | /api/status       | System status        |
| GET    | /api/history/<id> | Disk history         |
| POST   | /api/threshold    | Set alert thresholds |

---

## 🏗️ How It Works

* Backend collects disk data every **5 seconds**
* Frontend fetches data every **3 seconds**
* Alerts are triggered when thresholds are exceeded

---

## 🎨 Features

* Real-time disk monitoring
* Alert notifications (warning & critical)
* Usage history tracking
* Dark/Light mode
* CSV export

---

## 🛠️ Tech Stack

* Python (Flask)
* SQLite
* HTML, CSS, JavaScript

---

## 📌 Future Improvements

* Add email notifications
* Add multi-user support
* Improve UI design

---

⭐ Feel free to use, improve, and contribute!
