class DBError(Exception):
    def __init__(self, message: str):
        self.message = message


class ValidationError(DBError):
    pass


class NotFoundError(DBError):
    pass
