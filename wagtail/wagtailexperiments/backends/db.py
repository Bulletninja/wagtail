from __future__ import absolute_import, unicode_literals

import datetime

from django.db.models import F, Sum

from wagtail.wagtailexperiments.models import ExperimentHistory


def record_participant(experiment, user_id, variation, request):
    # abort if this user has participated already
    wagtailexperiments_started = request.session.get('wagtailexperiments_started', [])
    if experiment.id in wagtailexperiments_started:
        return

    wagtailexperiments_started.append(experiment.id)
    request.session['wagtailexperiments_started'] = wagtailexperiments_started

    # get or create a History record for this experiment variation and the current date
    history, _ = ExperimentHistory.objects.get_or_create(
        experiment=experiment, variation=variation, date=datetime.date.today()
    )
    # increment the participant_count
    ExperimentHistory.objects.filter(pk=history.pk).update(participant_count=F('participant_count') + 1)


def record_completion(experiment, user_id, variation, request):
    # abort if this user never started the experiment
    if experiment.id not in request.session.get('wagtailexperiments_started', []):
        return

    # abort if this user has completed already
    wagtailexperiments_completed = request.session.get('wagtailexperiments_completed', [])
    if experiment.id in wagtailexperiments_completed:
        return

    wagtailexperiments_completed.append(experiment.id)
    request.session['wagtailexperiments_completed'] = wagtailexperiments_completed

    # get or create a History record for this experiment variation and the current date
    history, _ = ExperimentHistory.objects.get_or_create(
        experiment=experiment, variation=variation, date=datetime.date.today()
    )
    # increment the completion_count
    ExperimentHistory.objects.filter(pk=history.pk).update(completion_count=F('completion_count') + 1)


def get_report(experiment):
    result = {}
    result.setdefault('variations', [])

    variations = experiment.get_variations()
    for variation in variations:
        history_entries = ExperimentHistory.objects.filter(experiment=experiment, variation=variation)

        variation_data = {
            'variation_pk': variation.pk,
            'is_control': variation.pk == experiment.control_page.pk,
            'is_winner': variation.pk == experiment.winning_variation.pk if experiment.winning_variation else False,
            'total_participant_count': history_entries.aggregate(sum=Sum('participant_count')).get('sum', 0),
            'total_completion_count': history_entries.aggregate(sum=Sum('completion_count')).get('sum', 0),
        }
        variation_data.setdefault('history', [])

        for entry in history_entries:
            variation_data['history'].append({
                'date': entry.date,
                'participant_count': entry.participant_count,
                'completion_count': entry.completion_count,
            })

        result['variations'].append(variation_data)

    return result
