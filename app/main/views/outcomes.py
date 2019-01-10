import datetime

from flask import abort, current_app, request
from dmapiclient.audit import AuditTypes

from .. import main
from ... import db
from ...models import AuditEvent, Outcome

from ...utils import (
    get_json_from_request,
    get_valid_page_or_1,
    json_has_required_keys,
    paginated_result_response,
    single_result_response,
    validate_and_return_updater_request,
)
from ...validation import validate_outcome_json_or_400


@main.route("/outcomes/<int:outcome_id>", methods=("GET",))
def get_outcome(outcome_id):
    outcome = Outcome.query.filter_by(external_id=outcome_id).first_or_404()

    return single_result_response("outcome", outcome), 200


@main.route("/outcomes/<int:outcome_id>", methods=("PUT",))
def update_outcome(outcome_id):
    uniform_now = datetime.datetime.utcnow()

    updater_json = validate_and_return_updater_request()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ["outcome"])
    outcome_json = json_payload["outcome"]

    validate_outcome_json_or_400(outcome_json)

    # fetch and lock Outcome row so we know writing this back won't overwrite any other updates to it that made
    # it in in the meantime
    outcome = db.session.query(Outcome).filter_by(
        external_id=outcome_id,
    ).with_for_update().first()

    if not outcome:
        abort(404, f"Outcome {outcome_id} not found")

    outcome.update_from_json(outcome_json)

    if outcome.completed_at is not None and outcome_json.get("completed") is False:
        abort(400, f"Can't un-complete outcome")
    if outcome.completed_at is None and outcome_json.get("completed") is True:
        # make a cursory check for existing Outcome collisions. we're not actually totally relying on this
        # to police the constraint - there is a database unique constraint that will do that for us in a transactionally
        # bulletproof way. we do this check here manually too to be able to give a nicer error message in the 99% case.
        if outcome.brief and outcome.brief.outcome:
            abort(400, "Brief {} already has a complete outcome: {}".format(
                outcome.brief_id,
                outcome.brief.outcome.external_id,
            ))
        if outcome.direct_award_project and outcome.direct_award_project.outcome:
            abort(400, "Direct award project {} already has a complete outcome: {}".format(
                outcome.direct_award_project_id,
                outcome.direct_award_project.outcome.external_id,
            ))

        outcome.completed_at = uniform_now
        complete_audit_event = AuditEvent(
            audit_type=AuditTypes.complete_outcome,
            user=updater_json['updated_by'],
            db_object=outcome,
            data={},
        )
        complete_audit_event.created_at = uniform_now
        db.session.add(complete_audit_event)

    update_audit_event = AuditEvent(
        audit_type=AuditTypes.update_outcome,
        user=updater_json['updated_by'],
        db_object=outcome,
        data=outcome_json,
    )
    update_audit_event.created_at = uniform_now
    db.session.add(update_audit_event)
    db.session.commit()

    return single_result_response("outcome", outcome), 200


@main.route("/outcomes", methods=("GET",))
def list_outcomes():
    # Because the external_id is random, it's probably best to, by default, do primary ordering by `completed_at`.
    # We do this because we want to minimize the amount of "shifting between pages" that happens to results as a result
    # of the presence/absence of Outcomes appearing in earlier pages (in rare curcumstances this can cause results to
    # "fall between the cracks" when a client is iterating through pages).
    # `completed_at` is assigned fairly monotonically and once an Outcome has a `completed_at` value set, it's fairly
    # permanent. Outcomes without `completed_at` set are going to be more volatile and so are put at the end.
    # `external_id` is used as the tie-breaker - it's permanent, but anything but monotonic in assignment.

    outcomes = Outcome.query.order_by(Outcome.completed_at.nullslast(), Outcome.external_id)

    page = get_valid_page_or_1()

    completed = request.args.get("completed")
    if completed is not None and completed.lower() in ("false", "true"):
        completed_bool = (completed.lower() == "true")
        outcomes = outcomes.filter(Outcome.completed_at.is_(None) != completed_bool)

    return paginated_result_response(
        result_name="outcomes",
        results_query=outcomes,
        page=page,
        per_page=current_app.config['DM_API_OUTCOMES_PAGE_SIZE'],
        endpoint='.list_outcomes',
        request_args=request.args,
    )
