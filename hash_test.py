from werkzeug.security import generate_password_hash

password = "admin123"
hashed = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
print("복사해서 쓸 비밀번호 해시:")
print(hashed)
