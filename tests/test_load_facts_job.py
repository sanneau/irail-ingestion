from datetime import date
from types import SimpleNamespace

import pandas as pd
import psycopg
import pytest

from irail_ingestion import load_facts_job
from irail_ingestion.load_facts_job import available_days, missing_days


def test_load_one_day_logs_failure(monkeypatch, tmp_path, caplog):
    calls = []

    # 1) Fabriquer les doublures (rien ne s'exécute encore)
    def fake_upsert(db, rows, run_date, started_at):
        raise psycopg.OperationalError("connexion perdue")

    def fake_log_failure(db, run_date, started_at, error):
        calls.append((run_date, error))

    # 2) Mettre les doublures à la place des vraies fonctions
    monkeypatch.setattr(
        load_facts_job, "load_settings", lambda: SimpleNamespace(silver_dir=tmp_path)
    )
    monkeypatch.setattr(load_facts_job, "load_db_settings", lambda: [])
    monkeypatch.setattr(load_facts_job.pd, "read_parquet", lambda x: pd.DataFrame())
    monkeypatch.setattr(load_facts_job, "departure_rows", lambda y: [])
    monkeypatch.setattr(load_facts_job, "upsert_fact_departures", fake_upsert)
    monkeypatch.setattr(load_facts_job, "log_load_failure", fake_log_failure)

    # 3) Lancer la vraie fonction
    result = load_facts_job.load_one_day(date(2026, 10, 2))

    # 4) Vérifier : le code de retour, l'échec journalisé, la date dans le log
    assert result == 1
    assert calls[0][0] == date(2026, 10, 2)
    assert "2026-10-02" in caplog.text


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
