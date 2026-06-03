# scratch_update_tokens.py
from db.connection import SessionLocal
from core.models import SocialAccount

def update_credentials():
    db = SessionLocal()
    try:
        print("Locating topvnsport social account...")
        social = db.query(SocialAccount).filter_by(account_name='topvnsport').first()
        if not social:
            print("Error: Account 'topvnsport' not found in database.")
            return
            
        print("Old Account ID:", social.account_id)
        
        # New credentials provided by the user
        new_token = "EAAYigFc8hHsBRoyUGv8J6wwBwFNEDwJcmGmJGaZAbA9ZB9NykvzZBBLWZBIMN8GkW0dxxAMY5xYZBm7AMydeKhEG7TVOve5t4cfRMdn0bmhmgki1EGBd5bSTWkw7lTdKWRMPx1JhNhsoT0vhXNehPpzEvmd1Prwu2D0FNwAJ8mAI4WkIZBb0uwncDc0L6DRLTQqAtl"
        new_account_id = "1336332588429387" #act_1336332588429387
        
        social.access_token = new_token
        social.account_id = new_account_id
        
        db.add(social)
        db.commit()
        print("SUCCESS! Credentials updated successfully in database!")
        print("New Account ID:", social.account_id)
        
    except Exception as e:
        print("Failed to update credentials:", e)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_credentials()
