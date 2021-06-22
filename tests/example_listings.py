# -*- coding: utf-8 -*-
from hypothesis import settings
from hypothesis.strategies import (
    fixed_dictionaries, lists,
    text, integers, text, none,
    composite, one_of,
    just)

from functools import partial
import re

settings.register_profile("unit", settings(
    database=None,
    max_examples=1,
))
settings.load_profile("unit")


_descriptive_alphabet = (
    # start with some normal alphanumerics
    "abcdefghijklmnopABCDEFGHIJKLMNOP123"
    # some characters likely to fudge up poor escaping
    "\"\'<&%"
    # some printable unicode oddities
    "£Ⰶⶼ"
    # various weird types of spaces
    " \u200d\u2029\u202f"
)
_nonspace_cluster_re = re.compile(r"\S+", flags=re.UNICODE)


# we use this filter against hypothesis-generated strings so we don't unnecessarily trigger
# min/max word limits
# hint: use partial for tinkering with the kwargs
def _word_count_filter(s, min_words=1, max_words=None):
    count = len(_nonspace_cluster_re.findall(s))
    return (
        min_words is None or min_words <= count
    ) and (
        max_words is None or count <= max_words
    )


@composite
def requirements_list(draw, length, answers=False):
    if answers:
        elements = text() if length is not None else one_of(text(), none())
    else:
        elements = text(min_size=1, max_size=300, alphabet=_descriptive_alphabet).filter(
            partial(_word_count_filter, max_words=30)
        )
    return draw(lists(
        elements=elements,
        min_size=length,
        max_size=length if length is not None else 10
    ))


_brief_response_availability = text(min_size=1, max_size=100, alphabet=_descriptive_alphabet).filter(
    _word_count_filter
)


def brief_response_data(essential_count=5, nice_to_have_count=5):
    return fixed_dictionaries({
        "essentialRequirements": requirements_list(essential_count, answers=True),
        "niceToHaveRequirements": requirements_list(nice_to_have_count, answers=True),
        "availability": _brief_response_availability,
        "respondToEmailAddress": just("supplier@email.com"),
    })


def specialists_brief_response_data(min_day_rate=1, max_day_rate=1000):
    return fixed_dictionaries({
        "essentialRequirements": requirements_list(5, answers=True),
        "niceToHaveRequirements": requirements_list(5, answers=True),
        "respondToEmailAddress": just("supplier@email.com"),
        "availability": _brief_response_availability,
        "dayRate": integers(min_value=min_day_rate, max_value=max_day_rate).map(lambda x: str(x)),
    })


def brief_data(essential_count=5, nice_to_have_count=5):
    return fixed_dictionaries({
        'specialistRole': just('developer'),
        'location': lists(elements=just(['ACT'])),
        'essentialRequirements': requirements_list(essential_count),
        'niceToHaveRequirements': requirements_list(nice_to_have_count),
    })
