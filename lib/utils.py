import os
import re

number_emojis = {
    0: "1️⃣",
    1: "2️⃣",
    2: "3️⃣",
    3: "4️⃣",
    4: "5️⃣",
    5: "❌",
}


def clear_audio_files(exclude: str = ''):
    dir_name = os.path.join(os.path.dirname(__file__), "audio")
    test = os.listdir(dir_name)
    for item in test:
        if item.endswith(".opus") and item not in exclude:
            os.remove(os.path.join(dir_name, item))


def convert_seconds_to_timestamp(seconds: int):
    units = {"hours": 3600, "minutes": 60, "seconds": 1}
    values = []
    for value in units.values():
        count = seconds // value
        seconds -= count * value
        values.append(count)
    if values[0] > 0:
        return f"{values[0]:02d}:{values[1]:02d}:{values[2]:02d}"
    return f"{values[1]:02d}:{values[2]:02d}"


def time_string_to_seconds(time_str):
    time_components = {
        'h': 3600,
        'hour': 3600,
        'hours': 3600,
        'm': 60,
        'min': 60,
        'mins': 60,
        'minute': 60,
        'minutes': 60,
        's': 1,
        'sec': 1,
        'secs': 1,
        'second': 1,
        'seconds': 1,
    }

    total_seconds = 0

    for match in re.finditer(r'(\d+)\s*([a-zA-Z]+)', time_str):
        quantity = int(match.group(1))
        unit = match.group(2).lower()

        if unit in time_components:
            total_seconds += quantity * time_components[unit]

    return total_seconds
