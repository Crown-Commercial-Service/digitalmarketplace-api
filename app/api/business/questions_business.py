from app.api.services import (
    audit_service,
    audit_types,
    briefs,
    brief_clarification_question_service,
    brief_question_service
)
from app.api.business.errors import (
    NotFoundError,
    ValidationError,
    UnauthorisedError
)
from app.models import (
    BriefClarificationQuestion
)


def get_counts(brief_id, questions=None, answers=None):
    if questions:
        questionsCount = len(questions)
    else:
        questionsCount = len(brief_question_service.get_questions(brief_id))

    if answers:
        answersCount = len(answers)
    else:
        answersCount = len(brief_clarification_question_service.get_answers(brief_id))

    return {
        "questions": questionsCount,
        "answers": answersCount
    }


def get_question(current_user, brief_id, question_id):
    brief = briefs.find(id=brief_id).one_or_none()
    if not brief:
        raise NotFoundError("Invalid brief id '{}'".format(brief_id))

    if not briefs.has_permission_to_brief(current_user.id, brief.id):
        raise UnauthorisedError('Unauthorised to publish answer')

    question = brief_question_service.find(id=question_id, brief_id=brief.id).one_or_none()
    question_result = None
    if question:
        question_result = {
            "id": question.id,
            "data": question.data
        }

    return {
        "question": question_result,
        "brief": {
            "title": brief.data.get('title'),
            "id": brief.id,
            "questionsCloseAt": brief.questions_closed_at,
            "closedAt": brief.closed_at,
            "internalReference": brief.data.get('internalReference')
        }
    }


def get_questions(current_user, brief_id):
    brief = briefs.find(id=brief_id).one_or_none()
    if not brief:
        raise NotFoundError("Invalid brief id '{}'".format(brief_id))

    if not briefs.has_permission_to_brief(current_user.id, brief.id):
        raise UnauthorisedError('Unauthorised to publish answer')

    questions = brief_question_service.get_questions(brief_id)

    return {
        "questions": questions,
        "brief": {
            "title": brief.data.get('title'),
            "id": brief.id,
            "closedAt": brief.closed_at,
            "internalReference": brief.data.get('internalReference')
        },
        "questionCount": get_counts(brief_id, questions=questions)
    }


def get_answers(brief_id):
    brief = briefs.find(id=brief_id).one_or_none()
    if not brief:
        raise NotFoundError("Invalid brief id '{}'".format(brief_id))

    answers = brief_clarification_question_service.get_answers(brief_id)

    return {
        "answers": answers,
        "brief": {
            "title": brief.data.get('title'),
            "id": brief.id,
            "closedAt": brief.closed_at,
            "internalReference": brief.data.get('internalReference')
        },
        "questionCount": get_counts(brief_id, answers=answers)
    }


def publish_answer(current_user, brief_id, data):
    brief = briefs.get(brief_id)
    if not brief:
        raise NotFoundError("Invalid brief id '{}'".format(brief_id))

    if not briefs.has_permission_to_brief(current_user.id, brief.id):
        raise UnauthorisedError('Unauthorised to publish answer')

    publish_question = data.get('question')
    if not publish_question:
        raise ValidationError('Question is required')

    answer = data.get('answer')
    if not answer:
        raise ValidationError('Answer is required')

    brief_clarification_question = brief_clarification_question_service.save(
        BriefClarificationQuestion(
            _brief_id=brief.id,
            question=publish_question,
            answer=answer,
            user_id=current_user.id
        )
    )

    question_id = data.get('questionId')
    if question_id:
        question = brief_question_service.get(question_id)
        if question.brief_id == brief.id:
            question.answered = True
            brief_question_service.save(question)

    audit_service.log_audit_event(
        audit_type=audit_types.create_brief_clarification_question,
        user=current_user.email_address,
        data={
            'briefId': brief.id
        },
        db_object=brief_clarification_question)
