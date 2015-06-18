from flask import jsonify

from .. import main
from ...models import Framework


@main.route('/frameworks', methods=['GET'])
def list_frameworks():
    frameworks = Framework.query.all()

    return jsonify(
        frameworks=[f.serialize() for f in frameworks]
    )
