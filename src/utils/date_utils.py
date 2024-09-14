from datetime import datetime


def get_load_date_today():
    return datetime.datetime.now().strftime("%Y%M%d")