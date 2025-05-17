from calc import add, calculate_percentage, calculate_simple_percentage

def test_add():
    assert add(5, 3) == 2

def test_calculate_percentage():
    assert calculate_percentage(5, 100) == 5
    assert calculate_percentage(10, 200) == 20
    assert calculate_percentage(0, 100) == 0
    assert calculate_percentage(100, 100) == 100
    assert calculate_percentage(50, 200) == 100

def test_calculate_simple_percentage():
    assert calculate_simple_percentage(5, 100) == 5
    assert calculate_simple_percentage(10, 200) == 20
    assert calculate_simple_percentage(0, 100) == 0
    assert calculate_simple_percentage(100, 100) == 100
    assert calculate_simple_percentage(50, 200) == 100