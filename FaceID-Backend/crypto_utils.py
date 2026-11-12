import numpy as np
from cryptography.fernet import Fernet

def generate_key() -> bytes :
    return Fernet.generate_key()

def encrypt_vector(vector:list ,key: bytes) -> bytes:
    arr = np.array(vector,dtype= np.float32)
    raw_bytes = arr.tobytes()
    return Fernet(key).encrypt(raw_bytes)
 
def decrypt_vector(encrypted: bytes, key: bytes) -> list:
    raw_bytes = Fernet(key).decrypt(bytes(encrypted))
    arr = np.frombuffer(raw_bytes, dtype=np.float32)
    return arr.tolist()