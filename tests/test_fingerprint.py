from failingstate.fingerprint import fingerprint, normalize_message


def fp(source='assert value == 3', message='expected 17 at /tmp/a', exception='AssertionError'):
    return fingerprint('tests/test_a.py', 'test_value', source, exception, message)

def test_cosmetic_pairs():
    assert fp() == fp('assert value==3  # comment', 'expected 99 at /var/b')
    assert normalize_message('id 123e4567-e89b-12d3-a456-426614174000') == 'id <uuid>'
    assert normalize_message('function at 0x7fab123') == normalize_message('function at 0x123abc')

def test_semantic_pairs():
    assert fp() != fp('assert value != 3')
    assert fp() != fp('assert value == 4')
    assert fp() != fp(exception='ValueError')
    assert fp() != fp(message='actual 17 at /tmp/a')
    assert fp() != fingerprint('tests/test_b.py', 'test_value', 'assert value == 3', 'AssertionError', 'expected 17 at /tmp/a')
