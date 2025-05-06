import random

DAYS = 5
PERIODS = 7

def generate_schedule(subject_sessions):
    """
    Generate a timetable with given subject sessions, ensuring no overlap.
    """
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


def generate_schedule_for_classes(class_subject_data):
    """
    Generate a timetable for all classes independently, with per-day subject constraints.
    """
    class_timetables = {}
    print(f"Generating schedule for classes: {class_subject_data}")
    for class_name, subject_data in class_subject_data.items():
        timetable = [[None for _ in range(PERIODS)] for _ in range(DAYS)]
        day_subject_count = {day: {} for day in range(DAYS)}  # Track subjects per day
        available_slots = [(d, p) for d in range(DAYS) for p in range(PERIODS)]
        random.shuffle(available_slots)

        subject_sessions = {s: c for s, c in subject_data.items() if c > 0}
        for subject, total_sessions in subject_sessions.items():
            # First pass: one per day
            days = list(range(DAYS))
            random.shuffle(days)
            placed = 0

            for day in days:
                if placed >= total_sessions:
                    break
                day_slots = [(d, p) for d, p in available_slots if d == day]
                random.shuffle(day_slots)
                for d, p in day_slots:
                    if timetable[d][p] is None and day_subject_count[d].get(subject, 0) == 0:
                        timetable[d][p] = subject
                        available_slots.remove((d, p))
                        day_subject_count[d][subject] = 1
                        placed += 1
                        break

            # Place remaining
            if placed < total_sessions:
                extra_slots = [slot for slot in available_slots]
                random.shuffle(extra_slots)
                for d, p in extra_slots:
                    if timetable[d][p] is None:
                        timetable[d][p] = subject
                        available_slots.remove((d, p))
                        day_subject_count[d][subject] = day_subject_count[d].get(subject, 0) + 1
                        placed += 1
                        if placed == total_sessions:
                            break

            if placed < total_sessions:
                print(f"⚠️ Warning: Could not place all {subject} sessions for class {class_name}")

        class_timetables[class_name] = timetable

    return class_timetables

