import datetime


class Now:
    def __str__(self):
        return datetime.datetime.now().strftime("%H:%M:%S")
