from settings import MAX_ANALOG_VALUE


def get_value_percentage(value:float) -> float:
    new_value = (value / MAX_ANALOG_VALUE) * 100
    return round(new_value,2)