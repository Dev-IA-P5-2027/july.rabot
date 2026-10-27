import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "airflow" / "dags"))

from random_users import RandomUserApi, UserStreamer, to_user_record  # noqa: E402

RAW_USER = {
    "gender": "female",
    "name": {"title": "Miss", "first": "Tanja", "last": "Vidić"},
    "location": {
        "street": {"number": 9011, "name": "Mirkovićeva"},
        "city": "Boljevac",
        "country": "Serbia",
        "postcode": 41064,
        "coordinates": {"latitude": "58.5179", "longitude": "72.3017"},
    },
    "email": "tanja.vidic@example.com",
    "login": {"uuid": "de41e826-5883-4b99-8d9d-cf05f018f8b2"},
}


class FakePublisher:
    def __init__(self):
        self.messages = []
        self.flushed = False

    def publish(self, key, value):
        self.messages.append((key, json.loads(value)))

    def flush(self):
        self.flushed = True


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def test_to_user_record_keeps_useful_fields():
    record = to_user_record(RAW_USER)

    assert record == {
        "id": "de41e826-5883-4b99-8d9d-cf05f018f8b2",
        "full_name": "Miss Tanja Vidić",
        "gender": "female",
        "address": "9011 Mirkovićeva",
        "city": "Boljevac",
        "country": "Serbia",
        "postcode": "41064",
        "latitude": 58.5179,
        "longitude": 72.3017,
        "email": "tanja.vidic@example.com",
    }


def test_to_user_record_accepts_postcode_with_letters():
    raw = json.loads(json.dumps(RAW_USER))
    raw["location"]["postcode"] = "W1 2AB"

    assert to_user_record(raw)["postcode"] == "W1 2AB"


def test_api_reads_first_result():
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return {"results": [RAW_USER]}

    assert RandomUserApi(fake_get, url="http://fake").fetch() == RAW_USER
    assert calls == ["http://fake"]


def test_streamer_sends_a_new_user_each_interval_then_flushes():
    users = iter([{**RAW_USER, "login": {"uuid": f"id-{i}"}} for i in range(10)])
    api = RandomUserApi(lambda url, timeout: {"results": [next(users)]})
    publisher = FakePublisher()
    clock = FakeClock()

    sent = UserStreamer(api, publisher, clock=clock, sleep=clock.sleep).run(duration_s=50, interval_s=10)

    assert sent == 5
    assert [key for key, _ in publisher.messages] == ["id-0", "id-1", "id-2", "id-3", "id-4"]
    assert publisher.flushed
