#!/usr/bin/env python
from sys import stdout

import sadisplay
from app import create_app
from app import models


def _build_desc():
    return sadisplay.describe(
        [getattr(models, attr) for attr in dir(models)],
        show_methods=True,
        show_properties=True,
        show_indexes=True,
    )


if __name__ == "__main__":
    app = create_app("development")
    with app.app_context():
        desc = _build_desc()
        stdout.write(sadisplay.dot(desc).encode("utf8"))
