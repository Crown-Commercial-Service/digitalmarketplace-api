import base64
import binascii
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from flask import abort
import hashlib
import math


class DataObscuringMixin:
    @staticmethod
    def __pad_as_bytes(val):
        """Converts an int to its equivalent in bytes and prepends with \x00 bytes until it's a multiple of 8 bytes
        long to create ciphertexts of the same length."""
        required_bytes = int(math.ceil(val.bit_length() / 32) * 8)
        return val.to_bytes(required_bytes, 'big')

    @staticmethod
    def __append_equals(text):
        """Appends '=' to the given text until it's a multiple of 8 characters long and so suitable for base32
        decoding."""
        l = len(text)
        return text + ''.join(['='] * int((math.ceil(l / 8) * 8) - l))

    @classmethod
    def __get_cipher(cls):
        """Instantiates a Cipher instance ready to 'encrypt'/obscure a given identifier. Seeds the encryptor
        with the DM secret obscuring key and a key derived from the name of the calling class to provide an extra
        'randomising' element."""
        from application import application

        shared_obscuring_key = int(application.config['DM_DATABASE_OBSCURING_KEY'], 16)
        database_obscuring_key = int(hashlib.sha256(cls.__name__.encode('utf-8')).hexdigest(), 16)

        derived_key = (shared_obscuring_key ^ database_obscuring_key).to_bytes(32, 'big')
        cipher = Cipher(algorithms.Blowfish(derived_key), modes.ECB(), default_backend())

        return cipher

    @classmethod
    def obscure(cls, original_id):
        """Obscures a provided identifier and cleans the return value. Works in 64-bit chunks, so the returned
        id will be a multiple of 13 characters long. While the obscured identifier is being encrypted, this is not
        suitable for sensitive information as the algorithm we are using is outdated, and the implementation details do
        not aim to provide strong cryptographic integrity."""
        encryptor = cls.__get_cipher().encryptor()

        padded_val = DataObscuringMixin.__pad_as_bytes(original_id)
        encrypted_id = encryptor.update(padded_val)
        obscured_id = base64.b32encode(encrypted_id)
        clean_obscured_id = obscured_id.decode('utf-8').strip('=').lower()

        return clean_obscured_id

    @classmethod
    def unobscure(cls, clean_obscured_id, raise_errors=False):
        """Unobscures a previously-disgused identifier and casts it back to an int. If the decryption or decoding
        fails at any point, we will 404, because it indicates an invalid resource."""
        decryptor = cls.__get_cipher().decryptor()

        obscured_id = DataObscuringMixin.__append_equals(clean_obscured_id.upper()).encode('utf-8')

        try:
            encrypted_id = base64.b32decode(obscured_id)
            padded_val = decryptor.update(encrypted_id)
            original_id = int.from_bytes(padded_val, 'big')

        except (binascii.Error, ValueError) as e:
            if raise_errors:
                raise ValueError('"{}" is not data obscured for {}'.format(clean_obscured_id,
                                                                           cls.__name__))

        else:
            return original_id

        abort(404)
