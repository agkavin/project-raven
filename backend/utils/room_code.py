"""
Utility functions for generating and managing room codes
"""
import random
import string
from typing import Set

# Avoid ambiguous characters: 0/O, 1/I/l
SAFE_CHARS = ''.join(set(string.ascii_uppercase + string.digits) - {'0', 'O', '1', 'I'})


def generate_room_code(length: int = 8, existing_codes: Set[str] = None) -> str:
    if existing_codes is None:
        existing_codes = set()

    max_attempts = 100
    for _ in range(max_attempts):
        code = ''.join(random.choices(SAFE_CHARS, k=length))
        if code not in existing_codes:
            return code

    base_code = ''.join(random.choices(SAFE_CHARS, k=length - 2))
    suffix = ''.join(random.choices(SAFE_CHARS, k=2))
    return base_code + suffix


def format_room_code(code: str, separator: str = '-') -> str:
    if len(code) == 8:
        return f"{code[:3]}{separator}{code[3:6]}{separator}{code[6:]}"
    elif len(code) == 6:
        return f"{code[:3]}{separator}{code[3:]}"
    return code


def validate_room_code_format(code: str) -> bool:
    clean_code = code.replace('-', '').replace(' ', '')
    if len(clean_code) not in [6, 8]:
        return False
    if not clean_code.isalnum():
        return False
    if not clean_code.isupper():
        return False
    return True


def normalize_room_code(code: str) -> str:
    return code.replace('-', '').replace(' ', '').upper()
