"""SuperMemo SM-2 Spaced Repetition Algorithm implementation."""
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass


@dataclass
class FlashcardReviewData:
    easiness: float = 2.5
    interval_days: int = 1
    repetitions: int = 0
    next_review: datetime = None


def calculate_next_review(current: FlashcardReviewData, quality: int) -> FlashcardReviewData:
    """
    Computes SM-2 intervals based on review quality (0 to 5):
    5 = perfect response
    4 = correct response after a hesitation
    3 = correct response recalled with serious difficulty
    2 = incorrect response; where the correct one seemed easy to recall
    1 = incorrect response; the correct one remembered
    0 = complete blackout
    """
    quality = max(0, min(5, quality))
    updated = FlashcardReviewData(
        easiness=current.easiness,
        interval_days=current.interval_days,
        repetitions=current.repetitions
    )

    # Calculate Easiness Factor (EF)
    # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    ef_change = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    updated.easiness = max(1.3, round(current.easiness + ef_change, 3))

    if quality < 3:
        # Failed recall: reset repetitions
        updated.repetitions = 0
        updated.interval_days = 1
    else:
        # Successful recall
        if current.repetitions == 0:
            updated.interval_days = 1
        elif current.repetitions == 1:
            updated.interval_days = 6
        else:
            updated.interval_days = max(1, round(current.interval_days * updated.easiness))
        updated.repetitions = current.repetitions + 1

    updated.next_review = datetime.now(timezone.utc) + timedelta(days=updated.interval_days)
    return updated
