# tests/test_fit_score.py

import pytest
from datetime import datetime
from services.classifier.fit_score import compute_fit_score
from services.classifier.classifier_types import FitScore

def test_compute_fit_score_deterministic():
    # Given fixed input stats
    company_id = "c_test"
    stats = {
        "techSignals": 0.5,
        "recentVolume": 1.0,
        "execChanges": 0.0,
        "sentiment": 0.8,
        "funding": 1.0,
    }

    # When
    score: FitScore = compute_fit_score(company_id, stats)

    # Then
    assert isinstance(score, FitScore)
    assert score.companyId == company_id
    assert 0 <= score.score <= 1
    assert "techSignals" in " ".join(score.reasons)
    assert isinstance(score.computedAt, datetime)

    # Running twice with same stats must give identical result
    score2: FitScore = compute_fit_score(company_id, stats)
    assert score.score == pytest.approx(score2.score)
    assert score.reasons == score2.reasons
