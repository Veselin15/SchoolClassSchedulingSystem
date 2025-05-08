import random
from typing import Dict, List, Tuple, Callable, Optional, Set
from collections import defaultdict

DAYS = 5
PERIODS = 7

Slot = Tuple[int, int]
Timetable = List[List[Optional[str]]]
TeacherAssignments = Dict[Slot, str]


def is_teacher_available(teacher_assignments_global, subject, slot, teacher_id):
    """
    Check if a teacher is available at a given slot.
    Returns False if the teacher is already assigned to another class for this subject at this slot.
    """
    return teacher_id not in teacher_assignments_global[subject][slot]


def count_teacher_workload(teacher_assignments_global, teacher_id):
    """
    Count how many slots a teacher is currently assigned across all subjects.
    Used to balance teacher workload.
    """
    count = 0
    for subject, slots in teacher_assignments_global.items():
        for slot, teachers in slots.items():
            if teacher_id in teachers:
                count += 1
    return count


def calculate_distribution_score(timetable: Timetable, subject: str) -> float:
    """
    Calculate how well distributed a subject is across the week.
    Higher score means better distribution.
    """
    # Count subject occurrences per day
    day_counts = [0] * DAYS
    for d in range(DAYS):
        for p in range(PERIODS):
            if timetable[d][p] == subject:
                day_counts[d] += 1

    # Penalize days with multiple sessions and reward even distribution
    distribution_score = 0
    for count in day_counts:
        if count > 0:
            # Reward for having the subject on this day
            distribution_score += 1
            # Penalize slightly for multiple sessions on same day
            if count > 1:
                distribution_score -= 0.2 * (count - 1)

    return distribution_score


def sort_slots_by_priority(
        timetable: Timetable,
        subject: str,
        existing_assignment_slots: Set[Slot]
) -> List[Slot]:
    """
    Sort slots by priority for better distribution:
    1. Prioritize days without the subject
    2. Avoid consecutive periods
    3. Balance periods across the day (avoid early/late clusters)
    4. Add slight randomness for variety
    """
    # Count subject occurrences per day and period
    day_counts = [0] * DAYS
    period_counts = [0] * PERIODS
    slots_per_day = [0] * DAYS  # Count total assigned slots per day

    for d in range(DAYS):
        for p in range(PERIODS):
            if timetable[d][p] is not None:
                slots_per_day[d] += 1
                if timetable[d][p] == subject:
                    day_counts[d] += 1
                    period_counts[p] += 1

    # Create all possible slots
    all_slots = []
    for d in range(DAYS):
        for p in range(PERIODS):
            if timetable[d][p] is None:  # Only consider empty slots
                # Calculate priority score (lower is better)
                priority = 0

                # PRIORITY 1: Distribute across days (most important)
                # Strongly prioritize days with no sessions of this subject
                if day_counts[d] == 0:
                    priority -= 15
                else:
                    # Penalize days that already have this subject
                    priority += day_counts[d] * 6

                # PRIORITY 2: Avoid consecutive periods
                has_adjacent = False
                if p > 0 and timetable[d][p - 1] == subject:
                    priority += 4
                    has_adjacent = True
                if p < PERIODS - 1 and timetable[d][p + 1] == subject:
                    priority += 4
                    has_adjacent = True

                # Extra penalty for being surrounded on both sides
                if p > 0 and p < PERIODS - 1 and timetable[d][p - 1] == subject and timetable[d][p + 1] == subject:
                    priority += 5

                # PRIORITY 3: Avoid same period across different days
                priority += period_counts[p] * 3

                # PRIORITY 4: Prefer days with fewer total sessions
                priority += slots_per_day[d] * 0.5

                # PRIORITY 5: Prefer middle periods over extremes
                # Calculate distance from middle period (better distribution)
                middle = PERIODS // 2
                distance_from_middle = abs(p - middle)
                priority += distance_from_middle * 0.2

                # Add small random factor
                priority += random.uniform(0, 1)

                all_slots.append(((d, p), priority))

    # Sort by priority (lower is better)
    all_slots.sort(key=lambda x: x[1])

    # Return just the slots
    return [slot for slot, _ in all_slots]


def backtrack_schedule(
        class_timetables: Dict[str, Dict],
        teacher_assignments_global: Dict,
        class_subject_teacher: Dict,
        get_teacher_for_subject: Callable,
        class_name: str,
        subject: str,
        sessions_left: int,
        all_subjects: Set[str],
        max_attempts: int = 200,  # Increased max attempts
        is_retry: bool = False  # Flag for retry attempts
) -> bool:
    """
    Enhanced backtracking algorithm with better slot selection strategy.
    """
    if sessions_left == 0:
        return True

    timetable = class_timetables[class_name]["timetable"]
    teacher_assignments = class_timetables[class_name]["teacher_assignments"][subject]
    teacher_id = class_subject_teacher[class_name][subject]

    # Get existing slots for this subject
    existing_slots = {slot for slot in teacher_assignments.keys()}

    # Sort slots optimally
    sorted_slots = sort_slots_by_priority(timetable, subject, existing_slots)

    # For retry attempts, consider all slots
    if is_retry:
        # Try all possible slots when in retry mode
        all_possible_slots = []
        for d in range(DAYS):
            for p in range(PERIODS):
                if timetable[d][p] is None:
                    all_possible_slots.append((d, p))
        # Add any missing slots to our sorted list
        for slot in all_possible_slots:
            if slot not in sorted_slots:
                sorted_slots.append(slot)

    # Limit attempts for efficiency but increase for difficult subjects
    attempts = 0

    for slot in sorted_slots:
        if attempts >= max_attempts:
            break

        attempts += 1
        d, p = slot

        if timetable[d][p] is not None:
            continue

        if not is_teacher_available(teacher_assignments_global, subject, slot, teacher_id):
            continue

        # In retry mode or for high-session subjects, be less picky about distribution
        skip_due_to_distribution = False
        if not is_retry:
            # Check if placing this subject creates a better distribution
            timetable[d][p] = subject
            current_score = calculate_distribution_score(timetable, subject)
            timetable[d][p] = None

            if current_score < 1.0 and sessions_left < 5 and attempts < max_attempts // 2:
                # Skip this slot if it creates poor distribution and we're not desperate yet
                skip_due_to_distribution = True

        if skip_due_to_distribution:
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
                sessions_left - 1, all_subjects, max_attempts, is_retry
        ):
            return True

        # Backtrack
        timetable[d][p] = None
        del teacher_assignments[slot]
        del teacher_assignments_global[subject][slot][teacher_id]

    return False


def optimize_existing_timetable(
        class_timetables: Dict[str, Dict],
        teacher_assignments_global: Dict,
        class_subject_teacher: Dict,
        get_teacher_for_subject: Callable
) -> bool:
    """
    Try to improve an existing timetable by relocating some sessions.
    """
    made_improvements = False

    for class_name, data in class_timetables.items():
        timetable = data["timetable"]

        # For each subject in this class
        for subject in data["teacher_assignments"]:
            # Get all slots where this subject is scheduled
            subject_slots = []
            for d in range(DAYS):
                for p in range(PERIODS):
                    if timetable[d][p] == subject:
                        subject_slots.append((d, p))

            # Skip if fewer than 2 sessions
            if len(subject_slots) < 2:
                continue

            # Calculate current distribution score
            current_score = calculate_distribution_score(timetable, subject)

            # Try relocating each session
            for old_slot in subject_slots:
                old_d, old_p = old_slot
                teacher_id = class_subject_teacher[class_name][subject]
                teacher = data["teacher_assignments"][subject][old_slot]

                # Remove session temporarily
                timetable[old_d][old_p] = None

                # Get all available slots
                available_slots = []
                for d in range(DAYS):
                    for p in range(PERIODS):
                        if timetable[d][p] is None and is_teacher_available(
                                teacher_assignments_global, subject, (d, p), teacher_id
                        ):
                            available_slots.append((d, p))

                # Try each available slot
                best_slot = None
                best_score = current_score

                for new_slot in available_slots:
                    if new_slot == old_slot:
                        continue

                    d, p = new_slot
                    timetable[d][p] = subject
                    score = calculate_distribution_score(timetable, subject)
                    timetable[d][p] = None

                    if score > best_score:
                        best_score = score
                        best_slot = new_slot

                # If found better position, move the session
                if best_slot and best_score > current_score:
                    d, p = best_slot
                    timetable[d][p] = subject

                    # Update teacher assignments
                    del data["teacher_assignments"][subject][old_slot]
                    del teacher_assignments_global[subject][old_slot][teacher_id]

                    data["teacher_assignments"][subject][best_slot] = teacher
                    teacher_assignments_global[subject][best_slot][teacher_id] = class_name

                    made_improvements = True
                else:
                    # Put back if no improvement
                    timetable[old_d][old_p] = subject

    return made_improvements


def get_priority_order(class_subject_data: Dict) -> List[Tuple[str, str]]:
    """
    Determine priority order for scheduling classes and subjects:
    1. Subjects with fewer teachers get highest priority
    2. Subjects with more sessions get higher priority
    3. Classes with more total sessions get priority

    This prioritization helps tackle the most constrained subjects first.
    """
    class_priorities = []

    # Calculate total sessions per class
    class_total_sessions = {}
    for class_name, subject_data in class_subject_data.items():
        total = sum(data["sessions"] for data in subject_data.values())
        class_total_sessions[class_name] = total

    # For each class, get its subjects in priority order
    for class_name, subject_data in class_subject_data.items():
        for subject, data in subject_data.items():
            if data["sessions"] == 0:
                continue

            # Modified priority: subjects with fewer teachers and more sessions come first
            # This helps ensure constrained subjects like Math and English get priority
            priority = (
                data["teachers"],  # Lower is higher priority (fewer teachers)
                -data["sessions"],  # Negative because higher is more priority
                -class_total_sessions[class_name],  # Negative because higher is more priority
            )

            class_priorities.append((priority, (class_name, subject)))

    # Sort by priority
    class_priorities.sort()

    # Return just the class-subject pairs in priority order
    return [item for _, item in class_priorities]


def generate_schedule_for_classes(class_subject_data, get_teacher_for_subject):
    """
    Enhanced schedule generator with better teacher allocation and subject distribution.

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

    # Collect all subjects
    all_subjects = set()
    for subject_data in class_subject_data.values():
        all_subjects.update(subject_data.keys())

    # Assign teachers more intelligently for each subject
    for subject in all_subjects:
        teacher_assignments_global[subject] = {(d, p): {} for d in range(DAYS) for p in range(PERIODS)}

        # Count how many classes need this subject
        classes_needing_subject = 0
        for class_name, subject_data in class_subject_data.items():
            if subject in subject_data and subject_data[subject]["sessions"] > 0:
                classes_needing_subject += 1

        # Now assign teachers to minimize conflicts
        teacher_counts = {}
        for class_name, subject_data in class_subject_data.items():
            if subject in subject_data and subject_data[subject]["sessions"] > 0:
                if class_name not in class_subject_teacher:
                    class_subject_teacher[class_name] = {}

                # Get max teachers available for this subject
                teachers = subject_data[subject]["teachers"]

                # Keep track of how many classes each teacher is assigned to
                for i in range(teachers):
                    if i not in teacher_counts:
                        teacher_counts[i] = 0

        # Assign teachers to classes, prioritizing less used teachers
        for class_name, subject_data in class_subject_data.items():
            if subject in subject_data and subject_data[subject]["sessions"] > 0:
                if subject not in class_subject_teacher[class_name]:
                    # Find teacher with minimum assignments
                    teachers = subject_data[subject]["teachers"]
                    min_count = float('inf')
                    best_teacher = 0

                    for i in range(teachers):
                        if i in teacher_counts and teacher_counts[i] < min_count:
                            min_count = teacher_counts[i]
                            best_teacher = i

                    # Assign this teacher
                    class_subject_teacher[class_name][subject] = best_teacher
                    teacher_counts[best_teacher] = teacher_counts.get(best_teacher, 0) + 1

    # Get priority order for scheduling
    priority_order = get_priority_order(class_subject_data)

    # Track failed scheduling attempts for retry
    failed_schedules = []

    # First pass: Schedule all subjects
    for class_name, subject in priority_order:
        total_sessions = class_subject_data[class_name][subject]["sessions"]
        if total_sessions == 0:
            continue

        success = backtrack_schedule(
            class_timetables, teacher_assignments_global, class_subject_teacher,
            get_teacher_for_subject, class_name, subject,
            total_sessions, all_subjects
        )

        if not success:
            print(f"⚠️ Warning: Could not place all {subject} sessions for class {class_name}. Will retry later.")
            failed_schedules.append((class_name, subject, total_sessions))

    # Second pass: Try to optimize distributions
    for _ in range(3):  # Try optimizing a few times
        if not optimize_existing_timetable(
                class_timetables, teacher_assignments_global, class_subject_teacher,
                get_teacher_for_subject
        ):
            break  # Stop if no improvements were made

    # Make space for failed schedules by removing lower priority sessions if needed
    if failed_schedules:
        print("Attempting to resolve scheduling conflicts...")
        # Try to make space for failed schedules
        make_space_for_failed_schedules(
            class_timetables, teacher_assignments_global, class_subject_teacher,
            class_subject_data, failed_schedules
        )

        # Third pass: Retry failed schedules with relaxed constraints
        for class_name, subject, total_sessions in failed_schedules:
            # Count how many sessions we already managed to place
            placed_sessions = 0
            timetable = class_timetables[class_name]["timetable"]
            for d in range(DAYS):
                for p in range(PERIODS):
                    if timetable[d][p] == subject:
                        placed_sessions += 1

            remaining_sessions = total_sessions - placed_sessions

            if remaining_sessions > 0:
                success = backtrack_schedule(
                    class_timetables, teacher_assignments_global, class_subject_teacher,
                    get_teacher_for_subject, class_name, subject,
                    remaining_sessions, all_subjects, max_attempts=300, is_retry=True
                )

                if not success:
                    print(f"❌ Final failure: Could not place all {subject} sessions for class {class_name}.")
                else:
                    print(f"✅ Successfully placed all remaining {subject} sessions for class {class_name} on retry.")

    return class_timetables


def make_space_for_failed_schedules(
        class_timetables, teacher_assignments_global, class_subject_teacher,
        class_subject_data, failed_schedules
):
    """
    Try to make space for failed schedules by temporarily removing some lower priority sessions.
    """
    # Get all classes and subjects in reverse priority order (least important first)
    priority_order = get_priority_order(class_subject_data)
    reverse_priority = list(reversed(priority_order))

    # Track slots that have been freed
    freed_slots = []

    # Map of classes and subjects that failed scheduling
    failed_map = {(class_name, subject) for class_name, subject, _ in failed_schedules}

    # Try removing some sessions from low priority subjects
    slots_to_free = min(len(failed_schedules) * 2, 10)  # Heuristic: free twice as many slots as failed schedules

    for class_name, subject in reverse_priority:
        # Skip if this is one of our failed schedules
        if (class_name, subject) in failed_map:
            continue

        timetable = class_timetables[class_name]["timetable"]
        teacher_assignments = class_timetables[class_name]["teacher_assignments"].get(subject, {})

        # Find all slots where this subject is scheduled
        subject_slots = []
        for d in range(DAYS):
            for p in range(PERIODS):
                if timetable[d][p] == subject:
                    subject_slots.append((d, p))

        # Skip if fewer than 2 sessions (don't remove if there's only 1)
        if len(subject_slots) <= 1:
            continue

        # Remove at most one session per subject to free up space
        if subject_slots and slots_to_free > 0:
            # Choose a slot to remove - prefer one that doesn't hurt distribution too much
            best_slot_to_remove = None
            best_score_after_removal = -float('inf')

            for slot in subject_slots:
                d, p = slot
                # Temporarily remove this session
                old_value = timetable[d][p]
                timetable[d][p] = None

                # Calculate distribution score without this session
                score = calculate_distribution_score(timetable, subject)

                # Restore the session
                timetable[d][p] = old_value

                if score > best_score_after_removal:
                    best_score_after_removal = score
                    best_slot_to_remove = slot

            if best_slot_to_remove:
                d, p = best_slot_to_remove

                # Remove this session
                teacher_id = class_subject_teacher[class_name][subject]

                # Make sure this slot exists in teacher assignments
                if best_slot_to_remove in teacher_assignments:
                    # Free the slot
                    timetable[d][p] = None
                    del teacher_assignments[best_slot_to_remove]
                    if teacher_id in teacher_assignments_global[subject][best_slot_to_remove]:
                        del teacher_assignments_global[subject][best_slot_to_remove][teacher_id]

                    freed_slots.append((class_name, subject, best_slot_to_remove))
                    slots_to_free -= 1

                    print(f"Temporarily removed a {subject} session from {class_name} to make space")

        if slots_to_free <= 0:
            break

    return freed_slots