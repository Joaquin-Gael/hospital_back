from typing import Tuple

from sqlmodel import Session, select

from app.db.main import engine
from app.models import User
from app.storage import storage

class EmailHasNotBeenVerified(Exception):
    def __init__(self, message: str = "Email has not been verified."):
        self.message = message
        super().__init__(self.message)
        
        
class UserAlreadyExists(Exception):
    def __init__(self, message: str = "User with this email already exists."):
        self.message = message
        super().__init__(self.message)


class UserRepository:
    @staticmethod
    def get_user_by_email(email: str, session: Session) -> User:
        statement = select(User).where(User.email == email)
        session_result = session.exec(statement)
        user: User = session_result.first()
        return user

    @staticmethod
    def create_user(user: User, session: Session) -> User:
        statement = select(User).where(User.email == user.email)
        session_result = session.exec(statement)
        existing_user: User = session_result.first()
        if existing_user:
            raise UserAlreadyExists(f"User with email {user.email} already exists.")
        user.set_password(user.password)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
        

    @staticmethod
    def update_user(user: User, session) -> User:
        with Session(engine) as session:
            session.merge(user)
            session.commit()
            return user
        
    @staticmethod
    def create_google_user(user_data: dict) -> Tuple[User, bool]:
        username = user_data.get('name')
        email = user_data.get('email')
        first_name = user_data.get('given_name')
        last_name = user_data.get('family_name')
        img_url = user_data.get('picture')
        has_email_verificated = user_data.get('verified_email')
        
        if not has_email_verificated:
            raise EmailHasNotBeenVerified()
        
        user = User(
            name=username,
            email=email,
            dni="00000000",  # Assuming 'id' is used as DNI
            is_active=True,
            is_superuser=False,
            is_admin=False,
            last_name=last_name,
            first_name=first_name,
            url_image_profile=img_url,
            
        )
        user.set_google_liked_acount_password(user_data.get('id'))
        
        with Session(engine) as session:
            existing_user = UserRepository.get_user_by_email(email, session)
            if existing_user:
                return existing_user, True
            
            session.add(user)
            session.commit()
            session.refresh(user)
            
        try:
            item = storage.get_by_parameter(parameter="email", equals=user.email, table_name="google-user-data")

            if not item:
                storage.set(key=str(user.id), value=user_data, table_name="google-user-data", long_live=True)
            else:
                storage.update(key=item.value.key, value=user_data, table_name="google-user-data")

        except Exception as e:
            print(__file__, e)
        
        return user, False