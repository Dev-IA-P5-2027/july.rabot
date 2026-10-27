"""Collecte d'utilisateurs fictifs depuis l'API randomuser.me et envoi vers une file de messages.

Chaque classe a un seul sujet ; les dépendances (client HTTP, éditeur de messages,
horloge) sont reçues à la construction pour pouvoir être remplacées par des faux en test.
"""

import json
import time
from typing import Callable, Protocol

RANDOM_USER_URL = "https://randomuser.me/api/"


class HttpGetter(Protocol):
    def __call__(self, url: str, timeout: float) -> dict: ...


class MessagePublisher(Protocol):
    def publish(self, key: str, value: bytes) -> None: ...

    def flush(self) -> None: ...


class RandomUserApi:
    """Récupère un utilisateur brut, tel que renvoyé par randomuser.me."""

    def __init__(self, http_get: HttpGetter, url: str = RANDOM_USER_URL):
        self._http_get = http_get
        self._url = url

    def fetch(self) -> dict:
        return self._http_get(self._url, timeout=10)["results"][0]


def to_user_record(raw: dict) -> dict:
    """Garde uniquement les champs utiles, dans le format attendu par la table Cassandra."""
    name = raw["name"]
    location = raw["location"]
    street = location["street"]
    return {
        "id": raw["login"]["uuid"],
        "full_name": f"{name['title']} {name['first']} {name['last']}",
        "gender": raw["gender"],
        "address": f"{street['number']} {street['name']}",
        "city": location["city"],
        "country": location["country"],
        # Texte et non entier : certains pays ont des codes postaux avec des lettres
        "postcode": str(location["postcode"]),
        "latitude": float(location["coordinates"]["latitude"]),
        "longitude": float(location["coordinates"]["longitude"]),
        "email": raw["email"],
    }


class UserStreamer:
    """Envoie un nouvel utilisateur à intervalle régulier pendant une durée donnée."""

    def __init__(
        self,
        api: RandomUserApi,
        publisher: MessagePublisher,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._api = api
        self._publisher = publisher
        self._clock = clock
        self._sleep = sleep

    def run(self, duration_s: float, interval_s: float) -> int:
        end = self._clock() + duration_s
        sent = 0
        while self._clock() < end:
            record = to_user_record(self._api.fetch())
            self._publisher.publish(record["id"], json.dumps(record).encode("utf-8"))
            sent += 1
            self._sleep(interval_s)
        self._publisher.flush()
        return sent
