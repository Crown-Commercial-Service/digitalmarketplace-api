from hypothesis import settings
from hypothesis.strategies import (
    fixed_dictionaries, lists,
    booleans, integers, text, none,
    composite, sampled_from, one_of,
    just)

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
        elements = text(min_size=1, average_size=10, max_size=300, alphabet='abcdefgh')
    return draw(lists(
        elements=elements,
        min_size=length,
        max_size=length if length is not None else 10
    ))


def brief_response_data(essential_count=5, nice_to_have_count=5):
    return fixed_dictionaries({
        "essentialRequirements": requirements_list(essential_count, answers=True),
        "niceToHaveRequirements": requirements_list(nice_to_have_count, answers=True),
        "availability": text(min_size=1, average_size=10, max_size=100, alphabet='abcdefghijkl'),
        "respondToEmailAddress": just("supplier@email.com"),
    })


def specialists_brief_response_data(min_day_rate=1, max_day_rate=1000):
    return fixed_dictionaries({
        "essentialRequirements": requirements_list(5, answers=True),
        "niceToHaveRequirements": requirements_list(5, answers=True),
        "respondToEmailAddress": just("supplier@email.com"),
        "availability": text(min_size=1, average_size=10, max_size=100, alphabet='abcdefghijkl'),
        "dayRate": integers(min_value=min_day_rate, max_value=max_day_rate).map(lambda x: str(x)),
    })


def brief_data(essential_count=5, nice_to_have_count=5):
    return fixed_dictionaries({
        'specialistRole': just('developer'),
        'location': text(min_size=1, average_size=10, alphabet='abcdefghijkl'),
        'essentialRequirements': requirements_list(essential_count),
        'niceToHaveRequirements': requirements_list(nice_to_have_count),
    })
