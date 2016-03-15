from Crypto.Cipher import AES, DES3
from Crypto import Random
import Crypto.Util.number as pn


def get_n_prime(n_bits):
    return pn.getPrime(512)

class AESCipher():
    def __init__(self, aes_key):
        self.key = aes_key

    def encrypt_data(self, plaintext):    
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        length = 16 - (len(plaintext) % 16) 
        plaintext += chr(length) * length 
        encrypted_text = iv + cipher.encrypt(plaintext)
        return encrypted_text
        

    def decrypt_data(self, encrypted_text):
        iv = encrypted_text[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        decrypted_text = cipher.decrypt(encrypted_text)
        decrypted_text = decrypted_text[16:-ord(decrypted_text[-1])]
        return decrypted_text


class DES3Cipher():
    def __init__(self, des3_key):
        self.key = des3_key

    def encrypt_data(self, plaintext):    
        iv = Random.new().read(DES3.block_size)
        cipher = DES3.new(self.key, DES3.MODE_CBC, iv)
        length = 8 - (len(plaintext) % 8) 
        plaintext += chr(length) * length 
        encrypted_text = iv + cipher.encrypt(plaintext)
        return encrypted_text
        

    def decrypt_data(self, encrypted_text):
        iv = encrypted_text[:8]
        cipher = DES3.new(self.key, DES3.MODE_CBC, iv)
        decrypted_text = cipher.decrypt(encrypted_text)
        decrypted_text = decrypted_text[8:-ord(decrypted_text[-1])]
        return decrypted_text