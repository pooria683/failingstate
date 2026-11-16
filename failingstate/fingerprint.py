"""Versioned fingerprint rules. Changes to these rules require community review."""
import ast
import hashlib
import json
import re

FINGERPRINT_VERSION = 1
_UUID = re.compile(r'\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b')
_PATH = re.compile(r'(?<![\w])(?:[A-Za-z]:[\\/]|/|\./|\.\./)(?:[^\s,:;\]\[()]+[\\/])*[^\s,:;\]\[()]+')
_ADDRESS = re.compile(r'\b0x[0-9a-fA-F]+\b')
_NUMBER = re.compile(r'(?<![\w])[-+]?\d+(?:\.\d+)?(?![\w])')


def normalize_message(message: str) -> str:
    message = _UUID.sub('<uuid>', message)
    message = _PATH.sub('<path>', message)
    message = _ADDRESS.sub('<address>', message)
    message = _NUMBER.sub('<number>', message)
    return ' '.join(message.split())


def normalize_source(source: str) -> str:
    """Ignore Python formatting/comments, but preserve operators and literal values."""
    try:
        return ast.dump(ast.parse(source.strip()), annotate_fields=True, include_attributes=False)
    except SyntaxError:
        # Incomplete source remains usable and stable across whitespace changes.
        return ' '.join(source.split())


def fingerprint(path: str, test: str, source: str, exception: str, message: str) -> str:
    fields = [FINGERPRINT_VERSION, path.replace('\\', '/'), test, normalize_source(source), exception, normalize_message(message)]
    payload = json.dumps(fields, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()
