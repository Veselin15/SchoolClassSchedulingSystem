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
    subject_teacher_pool = {}
    class_timetables = {}
    global_subject_slots = {(d, p): set() for d in range(DAYS) for p in range(PERIODS)}

    # Global teacher assignment tracker
    subject_teacher_usage = {}  # { "Math": {0: "Class A", 1: "Class B"} }

    for class_name, subject_data in class_subject_data.items():
        timetable = [[None for _ in range(PERIODS)] for _ in range(DAYS)]
        day_subject_count = {day: {} for day in range(DAYS)}
        available_slots = [(d, p) for d in range(DAYS) for p in range(PERIODS)]
        random.shuffle(available_slots)

        subject_sessions = {
            s: v["sessions"] for s, v in subject_data.items() if v["sessions"] > 0
        }
        subject_teachers = {
            s: v["teachers"] for s, v in subject_data.items()
        }

        assigned_teachers = {}  # subject -> teacher index assigned to this class

        for subject, teachers_count in subject_teachers.items():
            used_indices = subject_teacher_pool.get(subject, set())
            # Find the first available teacher index not yet used for this subject
            for idx in range(teachers_count):
                if idx not in used_indices:
                    assigned_teachers[subject] = idx
                    used_indices.add(idx)
                    subject_teacher_pool[subject] = used_indices
                    break
            else:
                # All teachers already assigned — fallback to round-robin or reuse
                assigned_teachers[subject] = random.randint(0, teachers_count - 1)

        # Store teacher assignments
        teacher_assignments = {subject: {} for subject in subject_sessions}

        for subject, total_sessions in subject_sessions.items():
            num_teachers = subject_teachers[subject]

            # Initialize subject in global map
            if subject not in subject_teacher_usage:
                subject_teacher_usage[subject] = {}

            used_teacher_ids = subject_teacher_usage[subject].keys()
            available_teacher_ids = [i for i in range(num_teachers) if i not in used_teacher_ids]

            if not available_teacher_ids:
                print(f"⚠️ Not enough teachers for subject '{subject}' to assign one per class. Class '{class_name}' will reuse a teacher.")
                # fallback: randomly choose from already used teachers
                assigned_teacher_id = random.choice(list(used_teacher_ids))
            else:
                assigned_teacher_id = random.choice(available_teacher_ids)

            # Register usage
            subject_teacher_usage[subject][assigned_teacher_id] = class_name

            # Place sessions
            days = list(range(DAYS))
            random.shuffle(days)
            placed = 0

            for day in days:
                if placed >= total_sessions:
                    break
                day_slots = [(d, p) for d, p in available_slots if d == day]
                random.shuffle(day_slots)
                for d, p in day_slots:
                    current_teachers_used = len([
                        cls for cls in global_subject_slots[(d, p)] if cls[0] == subject
                    ])
                    if (timetable[d][p] is None and
                        current_teachers_used < num_teachers and
                        day_subject_count[d].get(subject, 0) == 0):

                        timetable[d][p] = subject
                        teacher = get_teacher_for_subject(class_name, subject, d, p, assigned_teacher_id)
                        teacher_assignments[subject][(d, p)] = teacher
                        available_slots.remove((d, p))
                        day_subject_count[d][subject] = 1
                        global_subject_slots[(d, p)].add((subject, class_name))
                        placed += 1
                        break

            # Fill leftover sessions
            if placed < total_sessions:
                extra_slots = [slot for slot in available_slots]
                random.shuffle(extra_slots)
                for d, p in extra_slots:
                    current_teachers_used = len([
                        cls for cls in global_subject_slots[(d, p)] if cls[0] == subject
                    ])
                    if (timetable[d][p] is None and
                        current_teachers_used < num_teachers):

                        timetable[d][p] = subject
                        teacher = get_teacher_for_subject(class_name, subject, d, p, assigned_teacher_id)
                        teacher_assignments[subject][(d, p)] = teacher
                        available_slots.remove((d, p))
                        day_subject_count[d][subject] = day_subject_count[d].get(subject, 0) + 1
                        global_subject_slots[(d, p)].add((subject, class_name))
                        placed += 1
                        if placed == total_sessions:
                            break

            if placed < total_sessions:
                print(f"⚠️ Warning: Could not place all {subject} sessions for class {class_name}")

        class_timetables[class_name] = {
            "timetable": timetable,
            "teacher_assignments": teacher_assignments
        }

    return class_timetables

