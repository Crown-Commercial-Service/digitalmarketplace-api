from importlib import import_module
from werkzeug.routing import BaseConverter, ValidationError


class DataUnobscuringConverter(BaseConverter):
    """A URL routing converter that can be used to seamlessly unobscure/'decrypt' external IDs emitted by the API
    when they are received in an incoming URL/request.

    Example:
        @main.route('/direct-award/<obscured(DirectAwardProject):project_id>')

    In the above case, we are declaring a URL parameter 'project_id' that we are expecting to receive in incoming
    requests as obscured/external values (e.g. 'ehk7pl6pjidta') associated with the DirectAwardProject table, rather
    than the ID of the project in the given table (e.g. 1). When the URL is parsed, this converter tries to turn the
    external ID back into an internal (database) ID. If it succeeds, when Flask hands control over to the view, the
    value of 'project_id' will have been converted back to the internal ID. It it fails, Flask's routing will raise a
    404, effectively terminating the request before it reaches the view.

    In order to be resolved, the model must be imported into `app.models.__init__.py`. The application will not start
    if it cannot import the model you have referenced in a route, so there is no risk of this throwing errors due to
    typos when handling requests.
    """
    def __init__(self, url_map, model_name):
        """Takes the class name of a model and dynamically imports it and associates it with this custom converter
        so that it can correctly debofuscate the URL parameter."""
        super(DataUnobscuringConverter, self).__init__(url_map)
        self.model = getattr(import_module('app.models'), model_name)

    def to_python(self, value):
        """Takes an obscured ID (as passed to Flask's routing system) and attempts to unobscure it, transforming
        it back to the associated internal ID (e.g. a Direct Award Project/Saved Search PK/ID)."""
        # TODO: Remove this after buyer-fe re-direct for internal IDs has been removed.
        if value.isdigit() and len(value) <= 13:
            return int(value)

        try:
            unobscured_value = self.model.unobscure(value, raise_errors=True)

        except ValueError:
            # If we fail to unobscure the ID, this error will cause the route to not be recognised and 404.
            raise ValidationError()

        return unobscured_value

    def to_url(self, value):
        return str(value)
