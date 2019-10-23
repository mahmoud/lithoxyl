from lithoxyl.common import to_unicode


def test_to_unicode_doesnt_throw():
    to_unicode('hi')
    to_unicode('')
    to_unicode('\x81')
