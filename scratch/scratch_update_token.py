from core.dependencies import get_session
from core.models import SocialAccount

with get_session() as db:
    # Update all facebook accounts just to be sure we are using the new one
    accounts = db.query(SocialAccount).filter_by(platform='facebook').all()
    for acc in accounts:
        acc.access_token = 'EAAYigFc8hHsBRtfoxdJD1XWXEG4dHlaZADnmUpw13ZBYUiJZCpVYBzsjPEifLZC8W9EsDu03jiuEZBZCphJfZAmkMYu9qEeyvVjZBQvoQdWkQSGs2BKwuZCThmcDeEOYLJn7b4Df59bsOZBrQyNTWKy1DEtV2cbDaZCkyxNH7VUlErrlZCnsoWLfic1wIiKdY7zkAchrNcaY'
        acc.account_id = '313131084168462'
        acc.app_id = '' # Clear app_id so it uses dummy_app_id logic
        acc.app_secret = ''
    db.commit()
    print("Updated facebook accounts with new Page token and ad account.")
