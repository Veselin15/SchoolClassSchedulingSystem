import logging
import html
from typing import Any, Dict, List, Optional, Set, Tuple
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QPushButton, QTableWidget, QTableWidgetItem, QGridLayout,
    QScrollArea, QFrame, QMessageBox, QCheckBox, QGroupBox, QDialog, QTabWidget
)
from functools import partial
from scheduler.scheduler import generate_schedule_for_classes
from models.school_data import get_classes, get_subjects
from scheduler.scheduler import PERIODS, DAYS
from PyQt5.QtWidgets import QHeaderView

logging.basicConfig(level=logging.INFO)


class TimetableViewerWindow(QDialog):
    def __init__(self, parent: Optional[QWidget] = None, class_timetables: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(parent)
        self.class_timetables = class_timetables or {}
        self.init_ui()

    def init_ui(self) -> None:
        self.setWindowTitle("All Timetables View")
        self.setGeometry(50, 50, 1600, 900)  # Larger window size

        layout = QVBoxLayout(self)

        # Create a tab widget to display timetables
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)

        # Add tabs for each class
        for class_name, data in self.class_timetables.items():
            if not isinstance(data, dict) or "timetable" not in data:
                continue

            tab = QWidget()
            tab_layout = QVBoxLayout(tab)

            # Create table for this class
            table = self.create_timetable_for_class(class_name, data)
            tab_layout.addWidget(table)

            self.tab_widget.addTab(tab, f"Class {class_name}")

        layout.addWidget(self.tab_widget)

        # Add a close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        close_button.setFixedSize(150, 50)
        layout.addWidget(close_button, alignment=Qt.AlignCenter)

    def create_timetable_for_class(self, class_name: str, data: Dict[str, Any]) -> QTableWidget:
        table = QTableWidget(PERIODS, DAYS)
        table.setHorizontalHeaderLabels(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
        table.setVerticalHeaderLabels([f"Period {i + 1}" for i in range(PERIODS)])

        # Make the table bigger
        table.setMinimumHeight(700)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Set large column and row sizes
        for c in range(DAYS):
            table.setColumnWidth(c, 200)
        for r in range(PERIODS):
            table.setRowHeight(r, 80)

        # Fill the table with data
        timetable = data["timetable"]
        teacher_assignments = data.get("teacher_assignments", {})

        for day in range(DAYS):
            for period in range(PERIODS):
                subject = timetable[day][period]
                if subject:
                    # Find the teacher
                    teacher = "Unknown"
                    if subject in teacher_assignments and (day, period) in teacher_assignments[subject]:
                        teacher = teacher_assignments[subject][(day, period)]

                    item = QTableWidgetItem(f"{subject}\n{teacher}")
                    item.setTextAlignment(Qt.AlignCenter)
                    # Make the font larger
                    font = item.font()
                    font.setPointSize(12)
                    item.setFont(font)
                    table.setItem(period, day, item)

        return table


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.classes = get_classes()
        self.subjects = get_subjects()
        self.subject_spins: Dict[str, QSpinBox] = {}

        # Global settings for all classes
        self.global_subject_data: Dict[str, Dict[str, int]] = {
            subject: {"sessions": 0, "teachers": 1} for subject in self.subjects
        }

        # Initialize class_subject_data with global settings
        self.class_subject_data: Dict[str, Dict[str, Dict[str, int]]] = {
            class_name: {subject: {"sessions": 0, "teachers": 1} for subject in self.subjects}
            for class_name in self.classes
        }

        self.class_timetables: Dict[str, Any] = {}
        self.occupied_periods: Dict[str, Set[Any]] = {class_name: set() for class_name in self.classes}

        # For tracking consistent teacher assignments
        self.class_subject_teacher_mapping: Dict[str, Dict[str, int]] = {
            class_name: {} for class_name in self.classes
        }

        self.init_ui()

    def init_ui(self) -> None:
        self.setWindowTitle("School Class Scheduling System")
        self.setGeometry(100, 100, 1200, 700)

        layout = QVBoxLayout()

        # --- Global Settings Group ---
        global_group = QGroupBox("Global Subject Settings (Applied to All Classes)")
        global_layout = QVBoxLayout()

        # Add explanation
        explanation = QLabel(
            "Set the number of sessions and teachers for each subject. These settings will apply to all classes.")
        explanation.setWordWrap(True)
        global_layout.addWidget(explanation)

        # Grid for subject settings
        self.subject_layout = QGridLayout()

        # Add headers for the grid
        self.subject_layout.addWidget(QLabel("<b>Subject</b>"), 0, 0)
        self.subject_layout.addWidget(QLabel("<b>Sessions</b>"), 0, 1)
        self.subject_layout.addWidget(QLabel("<b>Teachers</b>"), 0, 2)

        self.subject_spins = {}
        for i, subject in enumerate(self.subjects):
            label = QLabel(subject)
            spin = QSpinBox()
            spin.setRange(0, 10)
            spin.setValue(0)
            spin.valueChanged.connect(partial(self.update_global_subject_data, subject))
            self.subject_spins[subject] = spin
            self.subject_layout.addWidget(label, i + 1, 0)
            self.subject_layout.addWidget(spin, i + 1, 1)

            teacher_spin = QSpinBox()
            teacher_spin.setRange(1, 5)
            teacher_spin.setValue(1)
            teacher_spin.valueChanged.connect(partial(self.update_global_subject_data, subject))
            self.subject_layout.addWidget(teacher_spin, i + 1, 2)
            self.subject_spins[f"{subject}_teachers"] = teacher_spin

        self.subject_layout.setColumnStretch(0, 1)
        self.subject_layout.setColumnStretch(1, 1)
        global_layout.addLayout(self.subject_layout)

        # Apply button
        apply_button = QPushButton("Apply Settings to All Classes")
        apply_button.clicked.connect(self.apply_global_settings)
        global_layout.addWidget(apply_button)

        global_group.setLayout(global_layout)
        layout.addWidget(global_group)

        # --- Class selection layout ---
        class_group = QGroupBox("Class Preview")
        class_layout = QVBoxLayout()

        class_selector = QHBoxLayout()
        class_selector.addWidget(QLabel("Select Class for Preview:"))
        self.class_combo = QComboBox()
        self.class_combo.addItems(self.classes)
        self.class_combo.currentTextChanged.connect(self.load_class_settings)
        class_selector.addWidget(self.class_combo)
        class_layout.addLayout(class_selector)

        # Display selected class info
        self.class_info = QLabel("Class settings will use global values")
        class_layout.addWidget(self.class_info)

        class_group.setLayout(class_layout)
        layout.addWidget(class_group)

        # --- Total periods display ---
        self.total_periods_label = QLabel("Total Periods per Week (All Classes): 0")
        layout.addWidget(self.total_periods_label)

        # --- Generate button ---
        button_layout = QHBoxLayout()

        self.schedule_button = QPushButton("Generate Schedules for All Classes")
        self.schedule_button.clicked.connect(self.generate_all_schedules)
        self.schedule_button.setFixedSize(250, 70)
        button_layout.addWidget(self.schedule_button, alignment=Qt.AlignCenter)

        # --- View All Timetables button ---
        self.view_all_button = QPushButton("View All Timetables")
        self.view_all_button.clicked.connect(self.open_timetable_viewer)
        self.view_all_button.setFixedSize(200, 70)
        self.view_all_button.setEnabled(False)  # Initially disabled until timetables are generated
        button_layout.addWidget(self.view_all_button, alignment=Qt.AlignCenter)

        # --- Clear button ---
        self.clear_button = QPushButton("Clear Timetables")
        self.clear_button.clicked.connect(self.clear_timetables)
        self.clear_button.setFixedSize(150, 70)
        button_layout.addWidget(self.clear_button, alignment=Qt.AlignCenter)

        layout.addLayout(button_layout)

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
        self.apply_global_settings()  # Initialize with global settings

    def update_total_periods_label(self) -> None:
        total_sessions = 0
        for subject, settings in self.global_subject_data.items():
            total_sessions += settings["sessions"]
        self.total_periods_label.setText(f"Total Periods per Week (For one class): {total_sessions}")

    def update_global_subject_data(self, subject: str) -> None:
        sessions = self.subject_spins[subject].value()
        teachers = self.subject_spins[f"{subject}_teachers"].value()

        # Update the global subject data
        self.global_subject_data[subject] = {
            "sessions": sessions,
            "teachers": teachers
        }

        self.update_total_periods_label()
        self.update_class_info()

    def apply_global_settings(self) -> None:
        # Apply global settings to all classes
        for class_name in self.classes:
            for subject in self.subjects:
                self.class_subject_data[class_name][subject] = {
                    "sessions": self.global_subject_data[subject]["sessions"],
                    "teachers": self.global_subject_data[subject]["teachers"]
                }

        # Update the UI
        self.update_total_periods_label()
        self.update_class_info()

    def load_class_settings(self, class_name: str) -> None:
        self.update_class_info()

    def update_class_info(self) -> None:
        class_name = html.escape(self.class_combo.currentText())
        info_lines = [f"<b>Class {class_name} Settings</b><br>", "Using global subject settings:<br>"]
        for subject in self.subjects:
            sessions = self.global_subject_data[subject]["sessions"]
            if sessions > 0:
                teachers = self.global_subject_data[subject]["teachers"]
                safe_subject = html.escape(subject)
                info_lines.append(f"• {safe_subject}: {sessions} sessions with {teachers} teacher(s)<br>")
        info_text = ''.join(info_lines)
        self.class_info.setText(info_text)

    def generate_all_schedules(self) -> None:
        try:
            # Clear the teacher mapping for a fresh start
            self.class_subject_teacher_mapping = {class_name: {} for class_name in self.classes}

            from scheduler.scheduler import generate_schedule_for_classes
            self.class_timetables = generate_schedule_for_classes(
                self.class_subject_data,
                self.get_teacher_for_subject
            )

            # Debug print to catch malformed data
            logging.info("Generated timetables:")
            for cls, table in self.class_timetables.items():
                logging.info("%s -> %s", cls, table)
                if not isinstance(table, dict) or "timetable" not in table:
                    logging.warning("⚠️ Problem with %s's timetable format.", cls)

            self.display_all_timetables()

            # Enable the View All button now that we have timetables
            self.view_all_button.setEnabled(True)

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
            import traceback
            traceback.print_exc()

    def display_all_timetables(self) -> None:
        # Clear existing timetables first
        while self.scroll_content_layout.count():
            item = self.scroll_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Display each class timetable separately for better visibility
        for class_name in self.classes:
            # Create a container for this class's timetable
            class_container = QFrame()
            class_container.setFrameShape(QFrame.Box)
            class_container.setLineWidth(1)
            class_layout = QVBoxLayout(class_container)

            class_title = QLabel(f"<h2>Class {html.escape(class_name)}</h2>")
            class_layout.addWidget(class_title)

            # Create timetable
            if class_name in self.class_timetables:
                timetable_data = self.class_timetables[class_name]
                if isinstance(timetable_data, dict) and "timetable" in timetable_data:
                    table = QTableWidget(PERIODS, DAYS)
                    table.setHorizontalHeaderLabels(["Mon", "Tue", "Wed", "Thu", "Fri"])
                    table.setVerticalHeaderLabels([f"Period {i + 1}" for i in range(PERIODS)])

                    # Make the table bigger and more readable
                    table.setMinimumHeight(400)  # Increased height
                    table.setMinimumWidth(600)  # Increased width

                    # Make sure all cells are visible
                    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                    table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

                    # Set fixed column and row sizes
                    for c in range(DAYS):
                        table.setColumnWidth(c, 120)
                    for r in range(PERIODS):
                        table.setRowHeight(r, 50)  # Increased row height

                    class_table = timetable_data["timetable"]
                    teacher_assignments = timetable_data.get("teacher_assignments", {})

                    # Process the table content
                    for day in range(DAYS):
                        for period in range(PERIODS):
                            subject = class_table[day][period]
                            if subject:
                                # Find the teacher for this specific period
                                teacher = "Unknown"
                                if subject in teacher_assignments and (day, period) in teacher_assignments[subject]:
                                    teacher = teacher_assignments[subject][(day, period)]

                                item = QTableWidgetItem(f"{subject}\n{teacher}")
                                item.setTextAlignment(Qt.AlignCenter)  # Center text in cell
                                table.setItem(period, day, item)

                    class_layout.addWidget(table)

            # Add this class container to the main layout
            self.scroll_content_layout.addWidget(class_container)

            # Add a small spacing between tables
            spacer = QLabel("")
            spacer.setFixedHeight(20)
            self.scroll_content_layout.addWidget(spacer)

    def check_for_overlaps(self) -> List[Tuple[int, int, List[str]]]:
        overlaps: List[Tuple[int, int, List[str]]] = []
        teacher_conflicts: Dict[str, Dict[Tuple[int, int], List[str]]] = {}

        for day_index in range(DAYS):
            for period in range(PERIODS):
                subject_to_classes: Dict[str, List[str]] = {}
                teacher_usage: Dict[str, Dict[int, List[str]]] = {}

                for class_name, timetable_data in self.class_timetables.items():
                    if isinstance(timetable_data, dict) and "timetable" in timetable_data:
                        timetable = timetable_data["timetable"]
                        teacher_assignments = timetable_data.get("teacher_assignments", {})
                    else:
                        logging.warning("⚠️ Invalid timetable for class %s: %s", class_name, timetable_data)
                        continue

                    if not isinstance(timetable, list) or len(timetable) != DAYS:
                        logging.warning("⚠️ Invalid structure in class %s: %s", class_name, timetable)
                        continue

                    subject = timetable[day_index][period]
                    if not subject:
                        continue

                    # Track classes by subject
                    if subject not in subject_to_classes:
                        subject_to_classes[subject] = []
                    subject_to_classes[subject].append(class_name)

                    # Extract teacher ID from the assignment
                    if subject in teacher_assignments and (day_index, period) in teacher_assignments[subject]:
                        teacher = teacher_assignments[subject][(day_index, period)]
                        # Extract teacher ID from format like "Math - T1"
                        teacher_id = None
                        if " - T" in teacher:
                            try:
                                teacher_id = int(teacher.split(" - T")[1]) - 1
                            except Exception:
                                teacher_id = None

                        if teacher_id is not None:
                            if subject not in teacher_usage:
                                teacher_usage[subject] = {}
                            if teacher_id not in teacher_usage[subject]:
                                teacher_usage[subject][teacher_id] = []
                            teacher_usage[subject][teacher_id].append(class_name)

                # Check for teacher conflicts
                for subject, teachers in teacher_usage.items():
                    for teacher_id, classes in teachers.items():
                        if len(classes) > 1:
                            if subject not in teacher_conflicts:
                                teacher_conflicts[subject] = {}
                            if (day_index, period) not in teacher_conflicts[subject]:
                                teacher_conflicts[subject][(day_index, period)] = []
                            teacher_conflicts[subject][(day_index, period)].extend(classes)
                            overlaps.append((day_index, period, classes))

                # Check for subject-teacher count conflicts
                for subject, class_list in subject_to_classes.items():
                    if len(class_list) > 1:
                        # Get teachers available for this subject
                        teachers_available = self.global_subject_data[subject]["teachers"]

                        if len(class_list) > teachers_available:
                            overlaps.append((day_index, period, class_list))

        return overlaps

    def get_teacher_for_subject(
        self,
        class_name: str,
        subject: str,
        day: int,
        period: int,
        teacher_index: int
    ) -> str:
        # Check if this class already has a teacher assigned for this subject
        if subject not in self.class_subject_teacher_mapping[class_name]:
            # Assign a consistent teacher ID for this class-subject combination
            self.class_subject_teacher_mapping[class_name][subject] = teacher_index

        # Use the consistently assigned teacher
        assigned_teacher_id = self.class_subject_teacher_mapping[class_name][subject]
        return f"{subject} - T{assigned_teacher_id + 1}"

    def open_timetable_viewer(self) -> None:
        """Open a new window with all timetables displayed in a larger format."""
        if not self.class_timetables:
            QMessageBox.warning(self, "No Timetables", "Please generate timetables first.")
            return

        viewer = TimetableViewerWindow(self, self.class_timetables)
        viewer.exec_()  # Modal dialog

    def clear_timetables(self) -> None:
        # Clear the timetable container
        while self.scroll_content_layout.count():
            item = self.scroll_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear the stored class timetables as well
        self.class_timetables = {}

        # Clear the teacher mapping
        self.class_subject_teacher_mapping = {class_name: {} for class_name in self.classes}

        # Disable the View All button since there are no timetables
        self.view_all_button.setEnabled(False)