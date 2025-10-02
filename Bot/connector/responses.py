class Responses:
    @staticmethod
    def ok(message: str) -> dict:
        return {"status": "ok", "message": message}

    @staticmethod
    def error(message: str) -> dict:
        return {"status": "error", "message": message}