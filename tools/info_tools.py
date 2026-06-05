import datetime

def get_current_datetime() -> str:
    """
    Returns the current date, day of the week, and time.
    Used by agents to resolve relative times like 'tomorrow', 'next week', etc.
    """
    now = datetime.datetime.now()
    return now.strftime("%A, %Y-%m-%d %H:%M:%S")
