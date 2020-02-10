
def is_open_to_all(brief):
    if brief.lot.slug == 'atm' or (
        brief.lot.slug == 'specialist' and brief.data.get('openTo') == 'all'
    ):
        return True

    return False
