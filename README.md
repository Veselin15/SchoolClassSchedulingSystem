# 🗓️ School Class Scheduling System

A Python-based application to manage and generate school class schedules. It uses a database backend (e.g., SQLite/MySQL) and provides tools to assign teachers, classrooms, time slots, and subjects intelligently.

## 🧩 Features

- **Create/update** teachers, students, classes, rooms, periods, and subjects.
- **Assign** subjects to class/section with teachers and rooms.
- **Auto-generate** conflict-free timetables based on constraints.
- **Export/print** schedules in readable formats.
- **CLI interface** (or GUI if implemented separately).

## 🛠️ Tech Stack

- **Language**: Python 3.x  
- **Database**: SQLite (default) or MySQL (optional)  
- **Libraries**: `sqlalchemy` (ORM), `pandas`, `prettytable`, etc.

## 🚀 Getting Started

### Prerequisites

- Python 3.7+  
- `pip` (package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Veselin15/SchoolClassSchedulingSystem.git
   cd SchoolClassSchedulingSystem
