from well import greet, hello


def test_hello():
    assert hello() == "hello from well"


def test_greet_default():
    assert greet() == "Hello, world!"


def test_greet_name():
    assert greet("Anna") == "Hello, Anna!"
