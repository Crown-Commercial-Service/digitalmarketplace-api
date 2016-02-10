from hypothesis import strategies, settings

settings.register_profile("unit", settings(
    database=None,
    max_examples=1,
))
settings.load_profile("unit")


def brief_data(essential_count=5):
    return strategies.fixed_dictionaries({
        "essentialRequirements": strategies.lists(
            elements=strategies.booleans(),
            min_size=essential_count, max_size=essential_count,
        )
    })
