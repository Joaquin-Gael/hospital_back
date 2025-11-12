from typing import Any, Dict, Tuple, Optional

from fastapi import Response
from sqlmodel import Session
from datetime import datetime, timedelta
from rich.console import Console

from orjson import loads
from urllib.parse import urlencode
import requests as r

from app.config import google_client_id, google_client_secret, cors_host, google_oauth_url, google_oauth_token_url, google_oauth_userinfo_url, debug
from app.core.auth import gen_token, encode
from app.core.interfaces.users import UserRepository
from app.models import User, AlertLevels, AlertDDoS

console= Console()

class AlertRepository:
    @classmethod
    async def create_alert_ddos(cls, session: Session, path: str, ip: str, alert_level: AlertLevels = AlertLevels.low) -> AlertDDoS:
        alert = AlertDDoS(
            path=path,
            ip=ip,
            alert_level=alert_level,
            count=1,
        )
        session.add(alert)
        session.commit()
        session.refresh(alert)
        return alert

class OauthCallbackError(Exception):
    def __init__(self, message: str = "Error during OAuth callback."):
        self.message = message
        super().__init__(self.message)

def get_user_data(access_token: str) -> Dict[str, str | bool | int | None]:
    headers = {'Authorization': f'Bearer {access_token}'}
    user_info_response = r.get(google_oauth_userinfo_url, headers=headers)
    user_data = loads(user_info_response.content)
    return user_data

def gen_token_from_user_data(user_data: User) -> str:
    payload = {
        "sub": str(user_data.id),
        "scopes": ["google", "user"]
    }
    
    return gen_token(payload=payload, refresh=False)


class OauthRepository:
    @staticmethod
    def google_oauth() -> Response:

        payload:Dict = {
            'client_id': google_client_id,
            'redirect_uri': f'{cors_host}/oauth/webhook/google_callback',
            'response_type':'code',
            'scope':'openid email profile',
            'access_type':'offline',
            'prompt':'select_account',
        }
        
        return Response(status_code=302, headers={"Location": f"{google_oauth_url}?{urlencode(payload)}"})

        
        
    @staticmethod
    def google_callback(code: str) -> Tuple[Dict[str, Any], bool, Response]:
        payload:Dict = {
            'client_id': google_client_id,
            'client_secret': google_client_secret,
            'redirect_uri': f'{cors_host}/oauth/webhook/google_callback',
            'grant_type': 'authorization_code',
            'code': code,
        }

        response = r.post(google_oauth_token_url, data=payload)

        data = loads(response.content.decode('utf-8'))
        
        if "error" in data:
            console.print("Error en data Oauth")
            raise OauthCallbackError(data["error"])
        
        user_data = get_user_data(data['access_token'])
        
        user, exist, audit = UserRepository.create_google_user(user_data)

        url_data = {
            "a":encode({"access_token":gen_token_from_user_data(user)}).hex()
        }

        return user_data, exist, audit, Response(
            status_code=302,
            headers={"Location": f"{cors_host}/user_panel?{urlencode(url_data)}" if not debug else f"http://localhost:4200/user_panel?{urlencode(url_data)}" }
        )