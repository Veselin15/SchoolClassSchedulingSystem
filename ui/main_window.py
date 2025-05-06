from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QPushButton, QTableWidget, QTableWidgetItem, QGridLayout,
    QScrollArea, QFrame, QMessageBox
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

        self.class_subject_data = {class_name: {subject: 0 for subject in self.subjects} for class_name in self.classes}
        self.class_timetables = {}

        self.occupied_periods = {class_name: set() for class_name in self.classes}

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        class_layout = QHBoxLayout()
        class_layout.addWidget(QLabel("Select Class for Preview:"))
        self.class_combo = QComboBox()
        self.class_combo.addItems(self.classes)
        self.class_combo.currentTextChanged.connect(self.load_class_settings)
        class_layout.addWidget(self.class_combo)
        layout.addLayout(class_layout)

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

        self.total_periods_label = QLabel("Total Periods per Week: 0")
        layout.addWidget(self.total_periods_label)

        self.schedule_button = QPushButton("Generate Schedules for All Classes")
        self.schedule_button.clicked.connect(self.generate_all_schedules)
        layout.addWidget(self.schedule_button)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.timetable_container = QWidget()
        self.timetable_layout = QVBoxLayout(self.timetable_container)
        self.scroll_area.setWidget(self.timetable_container)
        layout.addWidget(self.scroll_area)

        self.setLayout(layout)
        self.load_class_settings(self.class_combo.currentText())

    def update_total_periods_label(self):
        total = sum(spin.value() for spin in self.subject_spins.values())
        self.total_periods_label.setText(f"Total Periods per Week (All Classes): {total}")

    def load_class_settings(self, class_name):
        subject_data = self.class_subject_data.get(class_name, {})
        for subject, spin in self.subject_spins.items():
            spin.blockSignals(True)
            spin.setValue(subject_data.get(subject, 0))
            spin.blockSignals(False)
        self.update_total_periods_label()

    def update_class_subject_data(self, subject):
        value = self.subject_spins[subject].value()
        for cls in self.classes:
            self.class_subject_data[cls][subject] = value
        self.update_total_periods_label()

    def generate_all_schedules(self):
        try:
            from scheduler.scheduler import generate_schedule_for_classes
            self.class_timetables = generate_schedule_for_classes(self.class_subject_data)

            # Debug print to catch malformed data
            print("Generated timetables:")
            for cls, table in self.class_timetables.items():
                print(cls, "->", table)
                if not isinstance(table, list) or not all(isinstance(day, list) for day in table):
                    print(f"⚠️ Problem with {cls}'s timetable format.")

            self.display_all_timetables()

            overlaps = self.check_for_overlaps()
            if overlaps:
                msg = "Overlapping periods found:\n"
                for day, period, classes in overlaps:
                    msg += f"{['Mon', 'Tue', 'Wed', 'Thu', 'Fri'][day]}, Period {period + 1}: {', '.join(classes)}\n"
                QMessageBox.warning(self, "Overlap Warning", msg)
            else:
                QMessageBox.information(self, "No Overlaps", "No overlapping periods found.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def display_all_timetables(self):
        # Clear previous timetables
        print(f"Displaying timetables: {self.class_timetables}")
        for i in reversed(range(self.timetable_layout.count())):
            widget = self.timetable_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Use QGridLayout for 2-column display
        grid_layout = QGridLayout()

        for index, class_name in enumerate(self.classes):
            row = index // 2
            col = index % 2

            # Container widget for each timetable
            class_widget = QWidget()
            class_layout = QVBoxLayout(class_widget)

            class_layout.addWidget(QLabel(f"<b>Class {class_name}</b>"))
            table = QTableWidget(PERIODS, DAYS)
            table.setHorizontalHeaderLabels(["Mon", "Tue", "Wed", "Thu", "Fri"])
            table.setVerticalHeaderLabels([f"Period {i + 1}" for i in range(PERIODS)])

            if class_name in self.class_timetables:
                class_table = self.class_timetables[class_name]
                for day, periods in enumerate(class_table):
                    for period, subject in enumerate(periods):
                        if subject:
                            table.setItem(period, day, QTableWidgetItem(subject))
                if not any(any(period for period in day) for day in class_table):
                    table.setItem(0, 0, QTableWidgetItem("No subjects assigned"))

            table.setFrameStyle(QFrame.Panel | QFrame.Raised)
            class_layout.addWidget(table)

            grid_layout.addWidget(class_widget, row, col)

        # Replace existing layout
        for i in reversed(range(self.timetable_layout.count())):
            widget = self.timetable_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.timetable_layout.addLayout(grid_layout)

    def check_for_overlaps(self):
        overlaps = []
        for day_index in range(DAYS):
            for period in range(PERIODS):
                subject_to_classes = {}

                for class_name, timetable in self.class_timetables.items():
                    if not isinstance(timetable, list) or len(timetable) != DAYS:
                        print(f"⚠️ Invalid structure in class {class_name}")
                        continue

                    subject = timetable[day_index][period]
                    if not subject:
                        continue
                    if subject not in subject_to_classes:
                        subject_to_classes[subject] = []
                    subject_to_classes[subject].append(class_name)

                for subject, class_list in subject_to_classes.items():
                    if len(class_list) > 1:
                        overlaps.append((day_index, period, class_list))
        return overlaps
