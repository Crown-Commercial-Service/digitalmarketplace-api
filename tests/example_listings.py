from hypothesis import settings
from hypothesis.strategies import (
    fixed_dictionaries, lists,
    booleans, integers, text, none,
    composite, sampled_from, one_of,
)

settings.register_profile("unit", settings(
    database=None,
    max_examples=1,
))
settings.load_profile("unit")


@composite
def requirements_list(draw, length, answers=False):
    if answers:
        elements = booleans() if length is not None else one_of(booleans(), none())
    else:
        elements = text(min_size=1, alphabet='abcdefgh', average_size=10)
    return draw(lists(
        elements=elements,
        min_size=length,
        max_size=length if length is not None else 10
    ))


def brief_response_data(essential_count=5, nice_to_have_count=5):
    return fixed_dictionaries({
        "essentialRequirements": requirements_list(essential_count, answers=True),
        "niceToHaveRequirements": requirements_list(nice_to_have_count, answers=True),
    })


def brief_data(essential_count=5, nice_to_have_count=5):
    return fixed_dictionaries({
        'location': text(alphabet='abcdefghijkl'),
        'essentialRequirements': requirements_list(essential_count),
        'niceToHaveRequirements': requirements_list(nice_to_have_count),
    })
