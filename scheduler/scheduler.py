import random

DAYS = 5
PERIODS = 7


def generate_schedule(subject_sessions):
    timetable = [[None for _ in range(PERIODS)] for _ in range(DAYS)]
    slots = [(d, p) for d in range(DAYS) for p in range(PERIODS)]
    random.shuffle(slots)

    for subject, count in subject_sessions.items():
        placed = 0
        while placed < count and slots:
            d, p = slots.pop()
            if timetable[d][p] is None:
                timetable[d][p] = subject
                placed += 1
    return timetable


def generate_schedule_for_classes(class_subject_data, get_teacher_for_subject):
    class_timetables = {}
    global_subject_slots = {(d, p): set() for d in range(DAYS) for p in range(PERIODS)}

    # Track which teacher is assigned to which class for each subject and period
    # Format: {subject: {(day, period): {teacher_id: class_name}}}
    teacher_assignments_global = {}

    # First pass: create empty timetables and prepare the data
    for class_name, subject_data in class_subject_data.items():
        timetable = [[None for _ in range(PERIODS)] for _ in range(DAYS)]
        class_timetables[class_name] = {
            "timetable": timetable,
            "teacher_assignments": {subject: {} for subject, v in subject_data.items() if v["sessions"] > 0}
        }

    # Process each subject across all classes to distribute teachers evenly
    all_subjects = set()
    for subject_data in class_subject_data.values():
        all_subjects.update(subject_data.keys())

    # Track which teacher is assigned to which class for each subject
    # Format: {class_name: {subject: teacher_id}}
    class_subject_teacher = {}

    for subject in all_subjects:
        teacher_assignments_global[subject] = {(d, p): {} for d in range(DAYS) for p in range(PERIODS)}

        # Get classes that need this subject and how many teachers are available
        classes_needing_subject = []
        max_teachers = 0

        for class_name, subject_data in class_subject_data.items():
            if subject in subject_data and subject_data[subject]["sessions"] > 0:
                sessions = subject_data[subject]["sessions"]
                teachers = subject_data[subject]["teachers"]
                max_teachers = max(max_teachers, teachers)
                classes_needing_subject.append((class_name, sessions, teachers))

                # Initialize teacher tracking for this class if needed
                if class_name not in class_subject_teacher:
                    class_subject_teacher[class_name] = {}

        if not classes_needing_subject:
            continue

        # Sort by number of sessions (descending) to schedule more demanding classes first
        classes_needing_subject.sort(key=lambda x: x[1], reverse=True)

        # First, assign teachers to classes for consistency
        available_teacher_ids = list(range(max_teachers))
        random.shuffle(available_teacher_ids)

        for class_name, _, _ in classes_needing_subject:
            if subject not in class_subject_teacher[class_name] and available_teacher_ids:
                # Assign a teacher for this class-subject combination
                teacher_id = available_teacher_ids.pop(0)
                class_subject_teacher[class_name][subject] = teacher_id

                # If we run out of available teachers, start from the beginning
                if not available_teacher_ids:
                    available_teacher_ids = list(range(max_teachers))
                    random.shuffle(available_teacher_ids)

        # Now assign sessions for each class
        for class_name, total_sessions, _ in classes_needing_subject:
            timetable = class_timetables[class_name]["timetable"]
            teacher_assignments = class_timetables[class_name]["teacher_assignments"][subject]

            available_slots = [(d, p) for d in range(DAYS) for p in range(PERIODS) if timetable[d][p] is None]
            random.shuffle(available_slots)

            # Try to distribute sessions across different days
            day_subject_count = {day: 0 for day in range(DAYS)}
            placed = 0

            # First pass: try to place one session per day
            days = list(range(DAYS))
            random.shuffle(days)

            for day in days:
                if placed >= total_sessions:
                    break

                day_slots = [slot for slot in available_slots if slot[0] == day]
                if not day_slots:
                    continue

                for d, p in day_slots:
                    # Get the assigned teacher for this class and subject
                    teacher_id = class_subject_teacher[class_name].get(subject, 0)

                    # Check if this teacher is already busy at this time
                    if teacher_id in teacher_assignments_global[subject][(d, p)]:
                        continue

                    # Assign this teacher
                    timetable[d][p] = subject
                    teacher = get_teacher_for_subject(class_name, subject, d, p, teacher_id)
                    teacher_assignments[(d, p)] = teacher

                    # Mark this teacher as used for this period
                    teacher_assignments_global[subject][(d, p)][teacher_id] = class_name

                    # Remove slot from available slots
                    available_slots.remove((d, p))
                    day_subject_count[d] += 1
                    placed += 1
                    break

                if day_subject_count[d] > 0:
                    break  # Move to next day after placing one session

            # Second pass: place remaining sessions
            if placed < total_sessions:
                for d, p in available_slots[:]:
                    if placed >= total_sessions:
                        break

                    # Get the assigned teacher for this class and subject
                    teacher_id = class_subject_teacher[class_name].get(subject, 0)

                    # Check if this teacher is already busy at this time
                    if teacher_id in teacher_assignments_global[subject][(d, p)]:
                        continue

                    # Assign this teacher
                    timetable[d][p] = subject
                    teacher = get_teacher_for_subject(class_name, subject, d, p, teacher_id)
                    teacher_assignments[(d, p)] = teacher

                    # Mark this teacher as used for this period
                    teacher_assignments_global[subject][(d, p)][teacher_id] = class_name

                    # Remove slot from available slots
                    available_slots.remove((d, p))
                    placed += 1

            if placed < total_sessions:
                print(
                    f"⚠️ Warning: Could not place all {subject} sessions for class {class_name}. Placed {placed}/{total_sessions}")

    return class_timetables