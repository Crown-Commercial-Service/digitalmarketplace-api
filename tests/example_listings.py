from hypothesis import strategies, settings

settings.register_profile("unit", settings(
    database=None,
    max_examples=1,
))
settings.load_profile("unit")


def brief_response_data(essential_count=5, nice_to_have_count=5):
    return strategies.fixed_dictionaries({
        "essentialRequirements": strategies.lists(
            elements=strategies.booleans(),
            min_size=essential_count,
            max_size=essential_count,
        ),
        "niceToHaveRequirements": strategies.lists(
            elements=strategies.booleans(),
            min_size=nice_to_have_count,
            max_size=nice_to_have_count,
        ),
    })


def brief_data(essential_count=5, nice_to_have_count=5):
    return strategies.fixed_dictionaries({
        'essentialRequirements': strategies.lists(
            elements=strategies.text(min_size=1, alphabet='abcdefgh', average_size=10),
            min_size=essential_count,
            max_size=essential_count,
        ),
        'niceToHaveRequirements': strategies.lists(
            elements=strategies.text(min_size=1, alphabet='abcdefgh', average_size=10),
            min_size=nice_to_have_count,
            max_size=nice_to_have_count,
        ),
    })
