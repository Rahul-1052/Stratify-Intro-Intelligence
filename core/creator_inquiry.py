"""Evidence requirements for creator-selected concerns, not inferred diagnoses."""
FOCUS_REQUIREMENTS = {
    'reach': ['Views measured over the same time after publication', 'Impressions and traffic sources for the selected videos', 'Comparable topics and formats'],
    'returning_viewers': ['Returning-viewer analytics over a defined period', 'Publishing history and comparable content groups'],
    'subscriptions': ['Subscribers gained by video and relevant view counts over the same period', 'Traffic sources and comparable topics and formats'],
    'content_direction': ['The proposed topic and the creator’s goals', 'Examples of existing content and relevant audience feedback'],
    'packaging': ['The actual titles and thumbnail images', 'Impressions, click-through rates and traffic sources for comparable videos'],
    'watching': ['Video content and audience-retention curves', 'The intended viewing experience, including deliberate pacing or branding'],
    'open_question': ['A specific question and examples that show what the creator wants to understand'],
}


def inquiry_plan(brief):
    return {
        **brief,
        'source': 'creator_confirmed',
        'evidence_needed': FOCUS_REQUIREMENTS[brief['focus']],
        'status': 'scope_confirmed_not_answered',
    }
