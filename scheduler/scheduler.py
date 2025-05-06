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
    Generate a timetable for all classes, ensuring no overlapping periods and fitting within available slots.
    """
    class_timetables = {}  # Store timetables for each class
    occupied_periods = {class_name: set() for class_name in class_subject_data}  # Track occupied periods

    for class_name, subjects in class_subject_data.items():
        print(f"Generating timetable for {class_name}")  # Debugging statement
        timetable = [[None] * DAYS for _ in range(PERIODS)]  # Empty timetable for the class
        class_occupied = occupied_periods[class_name]  # Track the periods occupied by this class

        # Calculate total periods needed
        total_periods_needed = sum(subjects.values())
        available_slots = PERIODS * DAYS  # Total available slots (5 days * 7 periods)

        if total_periods_needed > available_slots:
            print(
                f"Warning: {class_name} has more periods requested ({total_periods_needed}) than available ({available_slots}).")
            # Limit total periods to available slots
            total_periods_needed = available_slots

            # Adjust the number of periods for subjects to fit
            adjusted_subjects = {}
            for subject, periods in subjects.items():
                adjusted_subjects[subject] = min(periods, available_slots)
                available_slots -= adjusted_subjects[subject]
                if available_slots <= 0:
                    break

            subjects = adjusted_subjects

        # Sort subjects by the number of periods to place smaller subjects first
        sorted_subjects = sorted(subjects.items(), key=lambda x: x[1])

        for subject, num_periods in sorted_subjects:
            print(f"Placing {num_periods} periods for {subject}")  # Debugging statement
            for _ in range(num_periods):
                assigned = False
                for period in range(PERIODS):
                    for day in range(DAYS):
                        # Check if the period is available and not occupied by another class
                        if timetable[period][day] is None and not any(
                                (period, day) in occupied_periods[other_class]
                                for other_class in occupied_periods if other_class != class_name
                        ):
                            timetable[period][day] = subject
                            class_occupied.add((period, day))  # Mark this period as occupied for the current class
                            assigned = True
                            break
                    if assigned:
                        break
                if not assigned:
                    print(f"Could not assign a period for {subject} after trying all slots.")  # Debugging statement

        class_timetables[class_name] = timetable
        print(f"Finished timetable for {class_name}")  # Debugging statement

    return class_timetables

