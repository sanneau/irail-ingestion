import pytest
import responses
from tenacity import wait_none

from irail_ingestion.client import (
    MAX_ATTEMPTS,
    fetch_liveboard,
    fetch_stations,
)
from irail_ingestion.exceptions import (
    InvalidRequestError,
    InvalidResponseError,
    TransientAPIError,
)

URL = "https://api.irail.be/v1/"
STATION = "BE.NMBS.008813003"
FAKE_STATION = "Atlantis"
URLLIVE = URL + "liveboard"
URLSTATION = URL + "stations"

ENDPOINTS = [
    pytest.param(fetch_liveboard, URLLIVE, (STATION,), id="liveboard"),
    pytest.param(fetch_stations, URLSTATION, (), id="stations"),
]


@responses.activate
def test_fetch_liveboard_returns_the_payload(settings, payload, b_session):
    # Arrange : « si quelqu'un fait un GET sur URL, réponds 200 avec ce JSON »
    responses.add(responses.GET, URLLIVE, json=payload, status=200)
    # Act
    result = fetch_liveboard(b_session, settings, STATION)

    # Assert
    assert result == payload
    assert len(responses.calls) == 1
    assert responses.calls[0].request.headers["User-Agent"] == "irail-test"


@responses.activate
def test_fetch_stations_return_payload(settings, payload_station, b_session):
    # Arrange : « si quelqu'un fait un GET sur URL, réponds 200 avec ce JSON »
    responses.add(responses.GET, URLSTATION, json=payload_station, status=200)

    # Act
    result = fetch_stations(b_session, settings)

    # Assert
    assert result == payload_station
    assert len(responses.calls) == 1
    assert responses.calls[0].request.headers["User-Agent"] == "irail-test"


@responses.activate
def test_fetch_stations_return_empty_station(settings, payload_station, b_session):
    payload_station["station"] = []
    responses.add(responses.GET, URLSTATION, json=payload_station, status=200)
    with pytest.raises(InvalidResponseError):
        fetch_stations(b_session, settings)
    assert len(responses.calls) == 1


@responses.activate
def test_fetch_stations_return_del_station_part(settings, payload_station, b_session):
    del payload_station["station"]
    responses.add(responses.GET, URLSTATION, json=payload_station, status=200)
    with pytest.raises(InvalidResponseError):
        fetch_stations(b_session, settings)
    assert len(responses.calls) == 1


@responses.activate
def test_stations_http_500_then_200_retries_and_succeeds(
    settings, payload_station, b_session
):
    # Arrange
    responses.add(responses.GET, URLSTATION, status=500)
    responses.add(responses.GET, URLSTATION, json=payload_station, status=200)
    fast_fetch = fetch_stations.retry_with(wait=wait_none())
    # Act
    result = fast_fetch(b_session, settings)
    # Assert
    assert result == payload_station
    assert len(responses.calls) == 2


@responses.activate
@pytest.mark.parametrize("fetch, url, args", ENDPOINTS)
def test_http_400_raises_invalid_request_without_retry(
    settings, b_session, fetch, url, args
):
    responses.add(
        responses.GET,
        url,
        body="Invalid Request",
        status=400,
    )
    # Act
    with pytest.raises(InvalidRequestError):
        fetch(b_session, settings, *args)
    # Assert
    assert len(responses.calls) == 1


@responses.activate
def test_liveboard_http_500_then_200_retries_and_succeeds(settings, payload, b_session):
    # Arrange
    responses.add(responses.GET, URLLIVE, status=500)
    responses.add(responses.GET, URLLIVE, json=payload, status=200)
    fast_fetch = fetch_liveboard.retry_with(wait=wait_none())
    # Act
    result = fast_fetch(b_session, settings, STATION)
    # Assert
    assert result == payload
    assert len(responses.calls) == 2


@responses.activate
@pytest.mark.parametrize("fetch, url, args", ENDPOINTS)
def test_repeated_500_gives_up_after_max_attempts(
    settings, b_session, fetch, url, args
):
    # Arrange
    responses.add(responses.GET, url, status=500)
    fast_fetch = fetch.retry_with(wait=wait_none())
    with pytest.raises(TransientAPIError):
        fast_fetch(b_session, settings, *args)

    assert len(responses.calls) == MAX_ATTEMPTS
