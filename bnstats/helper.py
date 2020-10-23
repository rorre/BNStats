def format_time(total: int) -> str:
    minutes = total // 60
    seconds = total % 60
    if seconds < 10:
        seconds = f"0{seconds}"  # type: ignore
    return f"{minutes}:{seconds}"
