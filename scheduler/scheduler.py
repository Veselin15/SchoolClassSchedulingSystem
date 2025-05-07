
import random
from typing import Dict, List, Tuple, Callable, Optional

DAYS = 5
PERIODS = 7

Slot = Tuple[int, int]
Timetable = List[List[Optional[str]]]
TeacherAssignments = Dict[Slot, str]

def is_teacher_available(teacher_assignments_global, subject, slot, teacher_id):
    return teacher_id not in teacher_assignments_global[subject][slot]

def backtrack_schedule(
    class_timetables: Dict[str, Dict],
    teacher_assignments_global: Dict,
    class_subject_teacher: Dict,
    get_teacher_for_subject: Callable,
    class_name: str,
    subject: str,
    sessions_left: int,
    slots: List[Slot]
) -> bool:
    if sessions_left == 0:
        return True

    timetable = class_timetables[class_name]["timetable"]
    teacher_assignments = class_timetables[class_name]["teacher_assignments"][subject]
    teacher_id = class_subject_teacher[class_name][subject]

    for slot in slots:
        d, p = slot
        if timetable[d][p] is not None:
            continue
        if not is_teacher_available(teacher_assignments_global, subject, slot, teacher_id):
            continue

        # Place session
        timetable[d][p] = subject
        teacher = get_teacher_for_subject(class_name, subject, d, p, teacher_id)
        teacher_assignments[slot] = teacher
        teacher_assignments_global[subject][slot][teacher_id] = class_name

        # Recurse
        if backtrack_schedule(
            class_timetables, teacher_assignments_global, class_subject_teacher,
            get_teacher_for_subject, class_name, subject,
            sessions_left - 1, slots
        ):
            return True

        # Backtrack
        timetable[d][p] = None
        del teacher_assignments[slot]
        del teacher_assignments_global[subject][slot][teacher_id]

    return False

def generate_schedule_for_classes(class_subject_data, get_teacher_for_subject):
    """
    Generates timetables for all classes using a backtracking algorithm to maximize session placement.
    :param class_subject_data: Dict[str, Dict[str, Dict[str, int]]] - class_name -> subject -> {"sessions": int, "teachers": int}
    :param get_teacher_for_subject: Callable - function to get teacher assignment
    :return: Dict[str, Dict] - class_name -> {"timetable": Timetable, "teacher_assignments": Dict}
    """
    class_timetables = {}
    teacher_assignments_global = {}
    class_subject_teacher = {}

    # Initialize timetables and teacher assignments
    for class_name, subject_data in class_subject_data.items():
        timetable = [[None for _ in range(PERIODS)] for _ in range(DAYS)]
        class_timetables[class_name] = {
            "timetable": timetable,
            "teacher_assignments": {subject: {} for subject, v in subject_data.items() if v["sessions"] > 0}
        }

    all_subjects = set()
    for subject_data in class_subject_data.values():
        all_subjects.update(subject_data.keys())

    # Assign teacher IDs for each class/subject and initialize global teacher assignments
    for subject in all_subjects:
        teacher_assignments_global[subject] = {(d, p): {} for d in range(DAYS) for p in range(PERIODS)}
        max_teachers = 0
        for class_name, subject_data in class_subject_data.items():
            if subject in subject_data and subject_data[subject]["sessions"] > 0:
                teachers = subject_data[subject]["teachers"]
                max_teachers = max(max_teachers, teachers)
                if class_name not in class_subject_teacher:
                    class_subject_teacher[class_name] = {}
        available_teacher_ids = list(range(max_teachers))
        random.shuffle(available_teacher_ids)
        for class_name, subject_data in class_subject_data.items():
            if subject in subject_data and subject_data[subject]["sessions"] > 0:
                if subject not in class_subject_teacher[class_name] and available_teacher_ids:
                    teacher_id = available_teacher_ids.pop(0)
                    class_subject_teacher[class_name][subject] = teacher_id
                    if not available_teacher_ids:
                        available_teacher_ids = list(range(max_teachers))
                        random.shuffle(available_teacher_ids)

    # Assign sessions for each class and subject using backtracking
    for class_name, subject_data in class_subject_data.items():
        for subject, v in subject_data.items():
            total_sessions = v["sessions"]
            if total_sessions == 0:
                continue
            slots = [(d, p) for d in range(DAYS) for p in range(PERIODS)]
            random.shuffle(slots)
            success = backtrack_schedule(
                class_timetables, teacher_assignments_global, class_subject_teacher,
                get_teacher_for_subject, class_name, subject,
                total_sessions, slots
            )
            if not success:
                print(f"⚠️ Warning: Could not place all {subject} sessions for class {class_name}.")

    return class_timetables
