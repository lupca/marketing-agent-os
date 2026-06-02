import os
import sys
import hashlib
import binascii

# Setup path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from core.dependencies import get_session
from core.models import User

def hash_password(password):
    """Tạo mã băm chuẩn dạng pbkdf2:sha256"""
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 150000)
    pwdhash = binascii.hexlify(pwdhash)
    return 'pbkdf2:sha256:150000$' + salt.decode('ascii') + '$' + pwdhash.decode('ascii')

def reset_admin_password():
    with get_session() as db:
        admin = db.query(User).filter_by(email="admin@marketingos.com").first()
        if admin:
            new_password = "MarketingOS2026!"
            admin.password_hash = hash_password(new_password)
            db.commit()
            print(f"Success! Mật khẩu cho {admin.email} đã được đổi thành: {new_password}")
        else:
            print("Error: Không tìm thấy tài khoản admin@marketingos.com")

if __name__ == "__main__":
    reset_admin_password()
