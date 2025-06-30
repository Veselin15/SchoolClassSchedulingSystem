# 🏫 School Class Scheduling System

A smart and flexible class scheduling system built using **Python** and **PyQt5** that allows schools to create optimized and conflict-free timetables for multiple classes, subjects, and teachers.

This application lets you:
- Define custom session counts per subject and class.
- Set teacher availability per subject.
- Automatically generate and visualize full weekly schedules.
- Detect and report overlapping teacher assignments.

---

## 📸 Preview

_(Add screenshots here of the GUI and generated timetable UI for better engagement)_

---

## ✨ Features

✅ **User-Friendly PyQt5 Interface**  
✅ **Per-Class Session Settings** (e.g., Class A has 5 Math sessions, Class B has 3)  
✅ **Global Teacher Allocation** (e.g., 3 teachers available for Physics)  
✅ **Apply Session Settings Across All Classes**  
✅ **One-Click Timetable Generation**  
✅ **Timetable Viewer with Tabbed Layout**  
✅ **Teacher Overlap Detection & Conflict Alerts**  
✅ **Scrollable Timetable Display with Subject + Teacher Names**  
✅ **Clear Timetables for Regeneration**

---

## 🧱 Architecture Overview

- **GUI**: `PyQt5`
- **Core Logic**: `scheduler.py` handles period planning and teacher distribution.
- **Data Layer**: `models/school_data.py` loads class and subject definitions.
- **Main UI**: `ui/main_window.py` orchestrates all user actions and scheduling.

---
