from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QPushButton, QTableWidget, QTableWidgetItem, QGridLayout,
    QScrollArea, QFrame, QMessageBox
)
from functools import partial
from scheduler.scheduler import generate_schedule
from models.school_data import get_classes, get_subjects
from scheduler.scheduler import PERIODS, DAYS
from PyQt5.QtWidgets import QHeaderView


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("School Class Scheduling System")
        self.setGeometry(100, 100, 1200, 700)

        self.classes = get_classes()
        self.subjects = get_subjects()
        self.subject_spins = {}

        self.class_subject_data = {
            class_name: {subject: {"sessions": 0, "teachers": 1} for subject in self.subjects}
            for class_name in self.classes
        }
        self.class_timetables = {}

        self.occupied_periods = {class_name: set() for class_name in self.classes}

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # --- Class selection layout ---
        class_layout = QHBoxLayout()
        class_layout.addWidget(QLabel("Select Class for Preview:"))
        self.class_combo = QComboBox()
        self.class_combo.addItems(self.classes)
        self.class_combo.currentTextChanged.connect(self.load_class_settings)
        class_layout.addWidget(self.class_combo)
        layout.addLayout(class_layout)

        # --- Subject spinboxes layout ---
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

            teacher_spin = QSpinBox()
            teacher_spin.setRange(1, 5)
            teacher_spin.setValue(1)
            self.subject_layout.addWidget(teacher_spin, i, 2)
            self.subject_spins[f"{subject}_teachers"] = teacher_spin

        self.subject_layout.setColumnStretch(0, 1)
        self.subject_layout.setColumnStretch(1, 1)
        layout.addLayout(self.subject_layout)

        # --- Total periods display ---
        self.total_periods_label = QLabel("Total Periods per Week: 0")
        layout.addWidget(self.total_periods_label)

        # --- Generate button ---
        self.schedule_button = QPushButton("Generate Schedules for All Classes")
        self.schedule_button.clicked.connect(self.generate_all_schedules)
        self.schedule_button.setFixedSize(250, 70)
        schedule_button_layout = QHBoxLayout()
        schedule_button_layout.addWidget(self.schedule_button, alignment=Qt.AlignCenter)
        layout.addLayout(schedule_button_layout)

        # --- Clear button ---
        self.clear_button = QPushButton("Clear Timetables")
        self.clear_button.clicked.connect(self.clear_timetables)
        self.clear_button.setFixedSize(150, 30)
        layout.addWidget(self.clear_button)

        # Scroll area that holds all generated grids
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        # Create a container widget inside the scroll area
        self.timetable_container = QWidget()
        self.scroll_content_layout = QVBoxLayout(self.timetable_container)
        self.timetable_container.setLayout(self.scroll_content_layout)
        self.scroll_area.setWidget(self.timetable_container)

        # Now add scroll area to main layout
        layout.addWidget(self.scroll_area)

        self.setLayout(layout)
        self.load_class_settings(self.class_combo.currentText())

    def update_total_periods_label(self):
        total = 0
        for subject, spin in self.subject_spins.items():
            if "_teachers" not in subject:  # Only consider session-related SpinBox
                sessions = spin.value()  # Get the number of sessions for the subject
                teacher_spin = self.subject_spins.get(f"{subject}_teachers", None)
                teachers = teacher_spin.value() if teacher_spin else 1  # Default to 1 if no teachers spinner
                total += sessions   # Add the number of sessions to the total
        self.total_periods_label.setText(f"Total Periods per Week (All Classes): {total}")

    def load_class_settings(self, class_name):
        subject_data = self.class_subject_data.get(class_name, {})
        for subject, spin in self.subject_spins.items():
            # Access the "sessions" value of the subject_data dictionary
            sessions = subject_data.get(subject, {}).get("sessions", 0)
            spin.blockSignals(True)
            spin.setValue(sessions)
            spin.blockSignals(False)
        self.update_total_periods_label()

    def update_class_subject_data(self, subject):
        sessions = self.subject_spins[subject].value()
        teachers = self.subject_spins[f"{subject}_teachers"].value()
        for cls in self.classes:
            self.class_subject_data[cls][subject] = {
                "sessions": sessions,
                "teachers": teachers
            }
        self.update_total_periods_label()  # Update the total periods label

    def generate_all_schedules(self):
        try:
            from scheduler.scheduler import generate_schedule_for_classes
            self.class_timetables = generate_schedule_for_classes(
                self.class_subject_data,
                self.get_teacher_for_subject
            )

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
        # Generate a new grid layout (2x2) for this batch of timetables
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)

        table_count = 0
        for index, class_name in enumerate(self.classes):
            row = table_count // 2
            col = table_count % 2
            table_count += 1

            class_widget = QWidget()
            class_layout = QVBoxLayout(class_widget)
            class_layout.addWidget(QLabel(f"<b>Class {class_name}</b>"))

            table = QTableWidget(PERIODS, DAYS)
            table.setHorizontalHeaderLabels(["Mon", "Tue", "Wed", "Thu", "Fri"])
            table.setVerticalHeaderLabels([f"Period {i + 1}" for i in range(PERIODS)])

            # Ensure the table fills all available space
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

            # Set fixed column and row sizes
            for c in range(DAYS):
                table.setColumnWidth(c, 170)
            for r in range(PERIODS):
                table.setRowHeight(r, 36)

            if class_name in self.class_timetables:
                class_table = self.class_timetables[class_name]["timetable"]
                teacher_assignments = self.class_timetables[class_name]["teacher_assignments"]
                for day, periods in enumerate(class_table):
                    for period, subject in enumerate(periods):
                        if subject:
                            teacher = teacher_assignments.get(subject, {}).get((day, period), "Unknown")
                            table.setItem(period, day, QTableWidgetItem(f"{subject}\n{teacher}"))

            class_layout.addWidget(table)
            grid_layout.addWidget(class_widget, row, col)

            # If 4 tables added, break early (or extend to more if needed)
            if table_count >= 4:
                break

        # Add this grid to the scrollable content layout
        self.scroll_content_layout.addWidget(grid_widget)

    def check_for_overlaps(self):
        overlaps = []
        for day_index in range(DAYS):
            for period in range(PERIODS):
                subject_to_classes = {}

                for class_name, timetable in self.class_timetables.items():
                    if isinstance(timetable, dict) and "timetable" in timetable:
                        timetable = timetable["timetable"]  # Extract timetable from class entry
                    else:
                        print(f"⚠️ Invalid timetable for class {class_name}: {timetable}")
                        continue

                    if not isinstance(timetable, list) or len(timetable) != DAYS:
                        print(f"⚠️ Invalid structure in class {class_name}: {timetable}")
                        continue

                    subject = timetable[day_index][period]
                    if not subject:
                        continue
                    if subject not in subject_to_classes:
                        subject_to_classes[subject] = []
                    subject_to_classes[subject].append(class_name)

                for subject, class_list in subject_to_classes.items():
                    # Sum of required teachers per class
                    total_needed = sum(self.class_subject_data[cls][subject]["teachers"] for cls in class_list)
                    available = max(self.class_subject_data[cls][subject]["teachers"] for cls in class_list)
                    if total_needed > available:
                        overlaps.append((day_index, period, class_list))
        return overlaps

    @staticmethod
    def get_teacher_for_subject(class_name, subject, day, period, teacher_index):
        return f"{subject} - T{teacher_index + 1}"

    def clear_timetables(self):
        # Clear the timetable container
        for i in range(self.scroll_content_layout.count()):
            item = self.scroll_content_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()  # Removes each widget (timetable) from the layout

        # Optionally, clear the stored class timetables as well
        self.class_timetables = {}