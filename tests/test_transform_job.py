import pandas as pd
import pytest

from irail_ingestion.transform_job import main


def test_job_writes_one_parquet(bronze_env):
    exit_code = main(["2026-09-24"])
    # --- Assert ---
    parquet = bronze_env / "silver" / "departures"
    parquet = parquet / "date=2026-09-24" / "departures.parquet"
    assert exit_code == 0
    assert parquet.exists()
    assert len(pd.read_parquet(parquet)) == 1


def test_job_is_idempotent(bronze_env):
    parquet = bronze_env / "silver" / "departures"
    parquet = parquet / "date=2026-09-24" / "departures.parquet"
    exit_code = main(["2026-09-24"])
    assert exit_code == 0
    first_passage = pd.read_parquet(parquet)

    exit_code = main(["2026-09-24"])
    assert exit_code == 0
    second_passage = pd.read_parquet(parquet)

    # --- Assert ---
    assert parquet.exists()
    assert len(pd.read_parquet(parquet)) == 1
    assert len(list(parquet.parent.iterdir())) == 1
    pd.testing.assert_frame_equal(first_passage, second_passage)


def test_invalid_date_exits_with_code_2(bronze_env):
    with pytest.raises(SystemExit) as excinfo:
        main(["2026-13-40"])
    assert excinfo.value.code == 2
