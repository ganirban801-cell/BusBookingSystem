
from pwdlib import PasswordHash

# Create Password Hashing System
password_hash = PasswordHash.recommended()


# Password Hash Function
def hash_password(password: str):
    return password_hash.hash(password)


# Password Verify Function
def verify_password(password: str, hashed_password: str):
    return password_hash.verify(password, hashed_password)
