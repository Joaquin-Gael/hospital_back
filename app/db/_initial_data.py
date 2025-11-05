from faker import Faker

import random

from rich.console import Console

from app.db.session import session_factory
from app.models import *

fake = Faker()

console = Console()

def generate_dni():
    return "".join([str(random.randint(0,9)) for _ in range(8)])

def get_blood_type() -> str:
    return random.choice(["A", "B", "AB", "O"]).join(random.choice(["+", "-"]))

def init_data(amount: int):
    console.rule("make init data")

    with session_factory() as session:
        for _ in range(amount):
            session.add(
                User(
                    name=fake.user_name(),
                    email=fake.email(),
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    address=fake.address(),
                    dni=generate_dni(),
                    telephone=fake.phone_number(),
                    blood_type=get_blood_type()
                ).set_password(fake.password())
            )

        session.commit()

        console.rule("Users created")