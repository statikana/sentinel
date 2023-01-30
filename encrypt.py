from cryptography.fernet import Fernet


class Encrypt:
    def __init__(self):
        self.key = input().encode()

    def encrypt(self, message: str) -> str:
        fernet = Fernet(self.key)
        return fernet.encrypt(message.encode()).decode()

    def decrypt(self, message: str) -> str:
        fernet = Fernet(self.key)
        return fernet.decrypt(message.encode()).decode()
