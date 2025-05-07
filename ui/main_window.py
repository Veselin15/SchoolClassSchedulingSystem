import logging
import html
from typing import Any, Dict, List, Optional, Tuple
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QPushButton, QTableWidget, QTableWidgetItem, QGridLayout,
    QScrollArea, QFrame, QMessageBox, QGroupBox, QDialog, QTabWidget
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
        self.setGeometry(50, 50, 1600, 900)
        layout = QVBoxLayout(self)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)

        for class_name, data in self.class_timetables.items():
            if not isinstance(data, dict) or "timetable" not in data:
                continue

            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            table = self.create_timetable_for_class(class_name, data)
            tab_layout.addWidget(table)
            self.tab_widget.addTab(tab, f"Class {class_name}")

        layout.addWidget(self.tab_widget)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        close_button.setFixedSize(150, 50)
        layout.addWidget(close_button, alignment=Qt.AlignCenter)

    def create_timetable_for_class(self, class_name: str, data: Dict[str, Any]) -> QTableWidget:
        table = QTableWidget(PERIODS, DAYS)
        table.setHorizontalHeaderLabels(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
        table.setVerticalHeaderLabels([f"Period {i + 1}" for i in range(PERIODS)])

        table.setMinimumHeight(700)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for c in range(DAYS):
            table.setColumnWidth(c, 200)
        for r in range(PERIODS):
            table.setRowHeight(r, 80)

        timetable = data["timetable"]
        teacher_assignments = data.get("teacher_assignments", {})

        for day in range(DAYS):
            for period in range(PERIODS):
                subject = timetable[day][period]
                if subject:
                    teacher = "Unknown"
                    if subject in teacher_assignments and (day, period) in teacher_assignments[subject]:
                        teacher = teacher_assignments[subject][(day, period)]

                    item = QTableWidgetItem(f"{subject}\n{teacher}")
                    item.setTextAlignment(Qt.AlignCenter)
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

        # Spinboxes for sessions (per class) and teachers (global)
        self.session_spins: Dict[str, QSpinBox] = {}
        self.teacher_spins: Dict[str, QSpinBox] = {}

        # Per-class session settings
        self.class_subject_sessions: Dict[str, Dict[str, int]] = {
            class_name: {subject: 0 for subject in self.subjects}
            for class_name in self.classes
        }

        # Global teacher settings
        self.global_subject_teachers: Dict[str, int] = {
            subject: 1 for subject in self.subjects
        }

        self.class_timetables: Dict[str, Any] = {}
        self.init_ui()

    def init_ui(self) -> None:
        self.setWindowTitle("School Class Scheduling System")
        self.setGeometry(100, 100, 1200, 700)
        layout = QVBoxLayout()

        # --- Settings Group ---
        settings_group = QGroupBox("Session and Teacher Settings")
        settings_layout = QVBoxLayout()

        # Add explanation
        explanation = QLabel(
            "Set the number of sessions for each subject (specific to selected class).<br>"
            "Set the number of teachers for each subject (applies to all classes).<br>"
            "Use 'Apply Settings to All Classes' to copy the current class's session settings to all other classes."
        )
        explanation.setWordWrap(True)
        settings_layout.addWidget(explanation)

        # Grid for subject settings
        self.subject_layout = QGridLayout()
        self.subject_layout.addWidget(QLabel("<b>Subject</b>"), 0, 0)
        self.subject_layout.addWidget(QLabel("<b>Sessions (per class)</b>"), 0, 1)
        self.subject_layout.addWidget(QLabel("<b>Teachers (global)</b>"), 0, 2)

        for i, subject in enumerate(self.subjects):
            label = QLabel(subject)

            # Session spinbox (per class)
            session_spin = QSpinBox()
            session_spin.setRange(0, 10)
            session_spin.setValue(0)
            session_spin.valueChanged.connect(partial(self.on_session_spin_changed, subject))
            self.session_spins[subject] = session_spin

            # Teacher spinbox (global)
            teacher_spin = QSpinBox()
            teacher_spin.setRange(1, 5)
            teacher_spin.setValue(1)
            teacher_spin.valueChanged.connect(partial(self.on_teacher_spin_changed, subject))
            self.teacher_spins[subject] = teacher_spin

            self.subject_layout.addWidget(label, i + 1, 0)
            self.subject_layout.addWidget(session_spin, i + 1, 1)
            self.subject_layout.addWidget(teacher_spin, i + 1, 2)

        self.subject_layout.setColumnStretch(0, 1)
        self.subject_layout.setColumnStretch(1, 1)
        self.subject_layout.setColumnStretch(2, 1)
        settings_layout.addLayout(self.subject_layout)

        # Apply to all button
        apply_button = QPushButton("Apply Settings to All Classes")
        apply_button.clicked.connect(self.apply_settings_to_all_classes)
        settings_layout.addWidget(apply_button)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # --- Class selection layout ---
        class_group = QGroupBox("Class Selection")
        class_layout = QVBoxLayout()

        class_selector = QHBoxLayout()
        class_selector.addWidget(QLabel("Select Class:"))
        self.class_combo = QComboBox()
        self.class_combo.addItems(self.classes)
        self.class_combo.currentTextChanged.connect(self.load_class_settings)
        class_selector.addWidget(self.class_combo)
        class_layout.addLayout(class_selector)

        # Display selected class info
        self.class_info = QLabel()
        class_layout.addWidget(self.class_info)

        class_group.setLayout(class_layout)
        layout.addWidget(class_group)

        # --- Generate and View buttons ---
        button_layout = QHBoxLayout()

        self.generate_button = QPushButton("Generate Schedules")
        self.generate_button.clicked.connect(self.generate_all_schedules)
        self.generate_button.setFixedSize(200, 50)
        button_layout.addWidget(self.generate_button)

        self.view_button = QPushButton("View All Timetables")
        self.view_button.clicked.connect(self.open_timetable_viewer)
        self.view_button.setFixedSize(200, 50)
        self.view_button.setEnabled(False)
        button_layout.addWidget(self.view_button)

        self.clear_button = QPushButton("Clear Timetables")
        self.clear_button.clicked.connect(self.clear_timetables)
        self.clear_button.setFixedSize(150, 50)
        button_layout.addWidget(self.clear_button)

        layout.addLayout(button_layout)

        # --- Timetable display area ---
        self.timetable_area = QScrollArea()
        self.timetable_area.setWidgetResizable(True)
        layout.addWidget(self.timetable_area)

        self.setLayout(layout)
        self.load_class_settings(self.class_combo.currentText())

    def load_class_settings(self, class_name: str) -> None:
        """Load the selected class's session settings into the UI."""
        for subject in self.subjects:
            # Update session spinbox with class-specific value
            self.session_spins[subject].blockSignals(True)
            self.session_spins[subject].setValue(self.class_subject_sessions[class_name][subject])
            self.session_spins[subject].blockSignals(False)

            # Update teacher spinbox with global value
            self.teacher_spins[subject].blockSignals(True)
            self.teacher_spins[subject].setValue(self.global_subject_teachers[subject])
            self.teacher_spins[subject].blockSignals(False)

        self.update_class_info()

    def on_session_spin_changed(self, subject: str) -> None:
        """Update the selected class's session count for the subject."""
        class_name = self.class_combo.currentText()
        self.class_subject_sessions[class_name][subject] = self.session_spins[subject].value()
        self.update_class_info()

    def on_teacher_spin_changed(self, subject: str) -> None:
        """Update the global teacher count for the subject."""
        self.global_subject_teachers[subject] = self.teacher_spins[subject].value()
        self.update_class_info()

    def apply_settings_to_all_classes(self) -> None:
        """Copy the current class's session settings to all other classes."""
        current_class = self.class_combo.currentText()
        for other_class in self.classes:
            if other_class != current_class:
                for subject in self.subjects:
                    self.class_subject_sessions[other_class][subject] = (
                        self.class_subject_sessions[current_class][subject]
                    )
        QMessageBox.information(
            self,
            "Settings Applied",
            f"Session settings from Class {current_class} have been applied to all other classes."
        )

    def generate_all_schedules(self) -> None:
        """Generate schedules using current settings."""
        try:
            # Build input data structure
            class_subject_data = {
                class_name: {
                    subject: {
                        "sessions": self.class_subject_sessions[class_name][subject],
                        "teachers": self.global_subject_teachers[subject]
                    }
                    for subject in self.subjects
                }
                for class_name in self.classes
            }

            # Generate schedules
            self.class_timetables = generate_schedule_for_classes(
                class_subject_data,
                self.get_teacher_for_subject
            )

            # Display results
            self.display_all_timetables()
            self.view_button.setEnabled(True)

            # Check for overlaps
            overlaps = self.check_for_overlaps()
            if overlaps:
                msg = "Teacher overlaps found:\n"
                for day, period, classes in overlaps:
                    msg += f"Day {day + 1}, Period {period + 1}: {', '.join(classes)}\n"
                QMessageBox.warning(self, "Scheduling Conflicts", msg)
            else:
                QMessageBox.information(self, "Success", "Schedules generated successfully with no conflicts!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate schedules: {str(e)}")
            logging.error("Schedule generation failed", exc_info=True)

    def count_sessions_per_class(self) -> Dict[str, int]:
        """
        Count the total number of sessions for each class across all subjects.

        Returns:
            Dict[str, int]: Dictionary mapping class names to their total session count
        """
        session_counts = {}
        for class_name in self.classes:
            total_sessions = sum(
                self.class_subject_sessions[class_name][subject]
                for subject in self.subjects
            )
            session_counts[class_name] = total_sessions
        return session_counts

    def update_class_info(self) -> None:
        """Update the class info display with session counts."""
        class_name = self.class_combo.currentText()
        info_lines = [f"<b>Class {html.escape(class_name)} Settings</b><br>"]

        # Show total sessions for this class
        total_sessions = sum(
            self.class_subject_sessions[class_name][subject]
            for subject in self.subjects
        )
        info_lines.append(f"<b>Total Sessions: {total_sessions}</b><br><br>")

        # Show sessions (class-specific) and teachers (global)
        for subject in self.subjects:
            sessions = self.class_subject_sessions[class_name][subject]
            if sessions > 0:
                teachers = self.global_subject_teachers[subject]
                safe_subject = html.escape(subject)
                info_lines.append(
                    f"• {safe_subject}: {sessions} sessions (class-specific), "
                    f"{teachers} teacher(s) (global)<br>"
                )

        # Show all class totals
        info_lines.append("<br><b>All Class Totals:</b><br>")
        session_counts = self.count_sessions_per_class()
        for cls, count in session_counts.items():
            info_lines.append(f"• {html.escape(cls)}: {count} sessions<br>")

        self.class_info.setText(''.join(info_lines))

    def display_all_timetables(self) -> None:
        """Display generated timetables in the scroll area."""
        container = QWidget()
        layout = QVBoxLayout()

        for class_name, data in self.class_timetables.items():
            group = QGroupBox(f"Timetable for {class_name}")
            group_layout = QVBoxLayout()

            if isinstance(data, dict) and "timetable" in data:
                table = QTableWidget(DAYS, PERIODS)
                table.setHorizontalHeaderLabels([f"Period {i + 1}" for i in range(PERIODS)])
                table.setVerticalHeaderLabels([f"Day {i + 1}" for i in range(DAYS)])

                timetable = data["timetable"]
                teacher_assignments = data.get("teacher_assignments", {})

                for d in range(DAYS):
                    for p in range(PERIODS):
                        subject = timetable[d][p]
                        if subject:
                            teacher = "Unknown"
                            if subject in teacher_assignments and (d, p) in teacher_assignments[subject]:
                                teacher = teacher_assignments[subject][(d, p)]
                            item = QTableWidgetItem(f"{subject}\n{teacher}")
                            table.setItem(d, p, item)

                table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
                group_layout.addWidget(table)

            group.setLayout(group_layout)
            layout.addWidget(group)

        container.setLayout(layout)
        self.timetable_area.setWidget(container)

    def check_for_overlaps(self) -> List[Tuple[int, int, List[str]]]:
        """Check for teacher assignment overlaps."""
        overlaps = []
        for day in range(DAYS):
            for period in range(PERIODS):
                teacher_classes = {}
                for class_name, data in self.class_timetables.items():
                    if isinstance(data, dict) and "timetable" in data:
                        subject = data["timetable"][day][period]
                        if subject:
                            teacher = None
                            if (subject in data.get("teacher_assignments", {}) and
                                    (day, period) in data["teacher_assignments"][subject]):
                                teacher = data["teacher_assignments"][subject][(day, period)]

                            if teacher:
                                if teacher not in teacher_classes:
                                    teacher_classes[teacher] = []
                                teacher_classes[teacher].append(class_name)

                for teacher, classes in teacher_classes.items():
                    if len(classes) > 1:
                        overlaps.append((day, period, classes))

        return overlaps

    def get_teacher_for_subject(
            self,
            class_name: str,
            subject: str,
            day: int,
            period: int,
            teacher_index: int
    ) -> str:
        """Generate teacher identifier string."""
        return f"{subject} - T{teacher_index + 1}"

    def open_timetable_viewer(self) -> None:
        """Open the timetable viewer window."""
        if not self.class_timetables:
            QMessageBox.warning(self, "No Timetables", "Please generate timetables first.")
            return

        viewer = TimetableViewerWindow(self, self.class_timetables)
        viewer.exec_()

    def clear_timetables(self) -> None:
        """Clear all generated timetables."""
        self.class_timetables.clear()
        self.timetable_area.setWidget(QWidget())
        self.view_button.setEnabled(False)
        QMessageBox.information(self, "Cleared", "All timetables have been cleared.")