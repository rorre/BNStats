def format_time(total):
    minutes = total // 60
    seconds = total % 60
    if seconds < 10:
        seconds = f"0{seconds}"
    return f"{minutes}:{seconds}"

    