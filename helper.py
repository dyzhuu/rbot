import os

number_emojis = {
    0: "1️⃣",
    1: "2️⃣",
    2: "3️⃣",
    3: "4️⃣",
    4: "5️⃣",
    5: "❌",
}


def delete_audio(exclude: str = ''):
    dir_name = os.path.join(os.path.dirname(__file__), "audio")
    test = os.listdir(dir_name)
    for item in test:
        if item.endswith(".opus") and item not in exclude:
            os.remove(os.path.join(dir_name, item))


def convert_seconds(seconds: int):

    units = {"hours": 3600, "minutes": 60, "seconds": 1}
    values = []
    for unit, value in units.items():
        count = seconds // value
        seconds -= count * value
        values.append(count)
    if values[0] > 0:
        return f"{values[0]:02d}:{values[1]:02d}:{values[2]:02d}"
    return f"{values[1]:02d}:{values[2]:02d}"
