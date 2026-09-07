from dataclasses import dataclass


@dataclass
class Director:
    director_name: str
    nationality: str = ""
