from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QPushButton, QTableWidget, QTableWidgetItem, QGridLayout,
    QScrollArea, QFrame
)
from functools import partial
from scheduler.scheduler import generate_schedule
from models.school_data import get_classes, get_subjects
from scheduler.scheduler import PERIODS, DAYS


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("School Class Scheduling System")
        self.setGeometry(100, 100, 1200, 700)

        self.classes = get_classes()
        self.subjects = get_subjects()
        self.subject_spins = {}

        # Each class will have its own data
        self.class_subject_data = {cls: {s: 0 for s in self.subjects} for cls in self.classes}
        # A dictionary to store each class's timetable
        self.class_timetables = {}

        # Global occupied periods (across all classes)
        self.occupied_periods = {class_name: set() for class_name in self.classes}

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Class selection (for subject config only)
        class_layout = QHBoxLayout()
        class_layout.addWidget(QLabel("Select Class for Preview:"))
        self.class_combo = QComboBox()
        self.class_combo.addItems(self.classes)
        self.class_combo.currentTextChanged.connect(self.load_class_settings)
        class_layout.addWidget(self.class_combo)
        layout.addLayout(class_layout)

        # Subject inputs
        self.subject_layout = QGridLayout()
        self.subject_spins = {}
        for i, subject in enumerate(self.subjects):
            label = QLabel(subject)
            spin = QSpinBox()
            spin.setRange(0, 10)
            spin.setValue(0)
            spin.valueChanged.connect(partial(self.update_class_subject_data, subject))
            self.subject_spins[subject] = spin
            self.subject_layout.addWidget(label, i, 0)
            self.subject_layout.addWidget(spin, i, 1)
        layout.addLayout(self.subject_layout)

        # Generate button
        self.schedule_button = QPushButton("Generate Schedules for All Classes")
        self.schedule_button.clicked.connect(self.generate_all_schedules)
        layout.addWidget(self.schedule_button)

        # Scroll area for all timetables
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.timetable_container = QWidget()
        self.timetable_layout = QVBoxLayout(self.timetable_container)
        self.scroll_area.setWidget(self.timetable_container)
        layout.addWidget(self.scroll_area)

        self.setLayout(layout)
        self.load_class_settings(self.class_combo.currentText())

    def load_class_settings(self, class_name):
        subject_data = self.class_subject_data.get(class_name, {})
        for subject, spin in self.subject_spins.items():
            spin.blockSignals(True)
            spin.setValue(subject_data.get(subject, 0))
            spin.blockSignals(False)

    def update_class_subject_data(self, subject):
        value = self.subject_spins[subject].value()
        for cls in self.classes:
            self.class_subject_data[cls][subject] = value

    def generate_all_schedules(self):
        from scheduler.scheduler import generate_schedule_for_classes
        print("Generating schedules for all classes...")  # Debugging statement
        self.class_timetables = generate_schedule_for_classes(self.class_subject_data)
        print("Schedules generated.")  # Debugging statement
        self.display_timetable(self.class_combo.currentText())

    def display_all_timetables(self):
        # Clear previous timetables
        for i in reversed(range(self.timetable_layout.count())):
            widget = self.timetable_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Display one table per class
        for class_name in self.classes:
            self.timetable_layout.addWidget(QLabel(f"<b>Class {class_name}</b>"))
            table = QTableWidget(PERIODS, DAYS)
            table.setHorizontalHeaderLabels(["Mon", "Tue", "Wed", "Thu", "Fri"])
            table.setVerticalHeaderLabels([f"Period {i + 1}" for i in range(PERIODS)])

            if class_name in self.class_timetables:
                class_table = self.class_timetables[class_name]
                for day, periods in enumerate(class_table):
                    for period, subject in enumerate(periods):
                        if subject:
                            table.setItem(period, day, QTableWidgetItem(subject))

            table.setFrameStyle(QFrame.Panel | QFrame.Raised)
            self.timetable_layout.addWidget(table)

