import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from pauses import Pauses, describe, restriction, retry_time

class PauseTests(unittest.TestCase):
    def test_restart_and_accounts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pause.db"
            Pauses(path).record("Mario", (100, 200))
            reopened = Pauses(path)
            self.assertIsNone(reopened.get("anna"))
            reopened.clear_verified("mario", 199)
            self.assertEqual(reopened.get("MARIO"), (100, 200))
            self.assertIn("terminata", describe(reopened.get("Mario"), 200))
            reopened.clear_verified("mario", 200)
            self.assertIsNone(reopened.get("mario"))

    def test_unknown_duration(self):
        self.assertIn("non ha indicato", describe((100, None), 10000))
        self.assertIsNone(retry_time("soon", 100))
        self.assertIsNone(retry_time("-1", 100))

    def test_http_date(self):
        self.assertEqual(retry_time("Thu, 01 Jan 1970 00:05:00 GMT", 100), 300)

    def test_wrapped_response(self):
        cause = Exception()
        cause.response = SimpleNamespace(status_code=429, headers={"Retry-After": "20"})
        error = Exception()
        error.__cause__ = cause
        self.assertEqual(restriction(error, 100), (100, 120))

    def test_connection_error(self):
        previous = SimpleNamespace(status_code=429, headers={})
        self.assertIsNone(restriction(TimeoutError(), 100, previous))

    def test_no_header(self):
        response = SimpleNamespace(status_code=429, headers={})
        self.assertEqual(restriction(Exception(), 123, response), (123, None))
