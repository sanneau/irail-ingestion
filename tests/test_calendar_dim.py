from datetime import date

import pytest

from irail_ingestion.calendar_dim import build_date_rows, time_band


@pytest.mark.parametrize(
    "start, end, expected_count, first_january, is_weekend",
    [pytest.param(date(2026, 1, 1), date(2030, 12, 31), 1826, True, False)],
)
def test_build_date_rows(start, end, expected_count, first_january, is_weekend):
    """Unit Test for build_date_rows function."""
    date_rows = build_date_rows(start, end)
    assert len(date_rows) == expected_count
    assert date_rows[0].is_holiday == first_january
    assert date_rows[3].is_holiday == is_weekend
    assert date_rows[1].is_holiday == is_weekend


@pytest.mark.parametrize(
    "year, expected_days",
    [(2027, 2), (2028, 3), (2100, 2)],  # 2100 : divisible par 100 mais pas par 400
)
def test_february_29_exists_only_in_leap_years(year, expected_days):
    rows = build_date_rows(date(year, 2, 28), date(year, 3, 1))

    assert len(rows) == expected_days
    assert any(r.date_key == year * 10000 + 229 for r in rows) is (expected_days == 3)


@pytest.mark.parametrize(
    "hour,expected_band",
    [
        (6, "morning_peak"),
        (8, "morning_peak"),
        (17, "evening_peak"),
        (19, "evening_peak"),
        (0, "night"),
        (5, "night"),
        (9, "morning"),
        (11, "morning"),
        (12, "noon"),
        (13, "noon"),
        (14, "afternoon"),
        (16, "afternoon"),
        (20, "evening"),
        (23, "evening"),
    ],
)
def test_time_bands(hour, expected_band):
    """Test that time bands are correctly assigned."""
    assert time_band(hour) == expected_band
