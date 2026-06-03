import sys
from core.dependencies import get_session
from core.models import SocialAccount

with get_session() as db:
    s = db.query(SocialAccount).filter_by(id='e8ff0c24-99ba-461a-9366-eb130b3de113').first()
    if s:
        print('ID:', s.id)
        print('Name:', s.account_name)
        print('Token:', s.access_token)
