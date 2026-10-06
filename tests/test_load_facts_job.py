from datetime import date

import pytest

from irail_ingestion.load_facts_job import available_days, missing_days

D25 = date(2026, 9, 25)
D26 = date(2026, 9, 26)
D27 = date(2026, 9, 27)


@pytest.mark.parametrize(
    ("available", "loaded", "expected"),
    [
        pytest.param({D25, D26, D27}, set(), [D25, D26, D27], id="rien-de-charge"),
        pytest.param({D25, D26, D27}, {D25, D26, D27}, [], id="tout-charge"),
        pytest.param({D25, D26, D27}, {D26}, [D25, D27], id="trou-au-milieu"),
        pytest.param({D27, D25}, set(), [D25, D27], id="resultat-trie"),
        pytest.param({D25}, {D25, D26}, [], id="journal-plus-large-que-silver"),
        pytest.param(set(), set(), [], id="silver-vide"),
    ],
)
def test_missing_days(available, loaded, expected):
    assert missing_days(available, loaded) == expected


def test_available_days(tmp_path):
    (tmp_path / "date=2026-09-25").mkdir()
    (tmp_path / "date=2026-09-26").mkdir()
    (tmp_path / "autre_dossier").mkdir()

    assert available_days(tmp_path) == {D25, D26}
