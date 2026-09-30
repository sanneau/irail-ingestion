import pytest
import responses
from tenacity import wait_none

from irail_ingestion.client import (
    MAX_ATTEMPTS,
    build_session,
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


@responses.activate
def test_fetch_liveboard_returns_the_payload(settings, payload):
    # Arrange : « si quelqu'un fait un GET sur URL, réponds 200 avec ce JSON »
    responses.add(responses.GET, URLLIVE, json=payload, status=200)
    session = build_session(settings)

    # Act
    result = fetch_liveboard(session, settings, STATION)

    # Assert
    assert result == payload
    assert len(responses.calls) == 1
    assert responses.calls[0].request.headers["User-Agent"] == "irail-test"


@responses.activate
def test_fetch_stations_return_payload(settings, payload_station):
    # Arrange : « si quelqu'un fait un GET sur URL, réponds 200 avec ce JSON »
    responses.add(responses.GET, URLSTATION, json=payload_station, status=200)
    session = build_session(settings)

    # Act
    result = fetch_stations(session, settings)

    # Assert
    assert result == payload_station
    assert len(responses.calls) == 1
    assert responses.calls[0].request.headers["User-Agent"] == "irail-test"


@responses.activate
def test_fetch_stations_return_empty_station(settings, payload_station):
    payload_station["station"] = []
    responses.add(responses.GET, URLSTATION, json=payload_station, status=200)
    session = build_session(settings)
    with pytest.raises(InvalidResponseError):
        fetch_stations(session, settings)
    assert len(responses.calls) == 1


@responses.activate
def test_fetch_stations_return_del_station_part(settings, payload_station):
    del payload_station["station"]
    responses.add(responses.GET, URLSTATION, json=payload_station, status=200)
    session = build_session(settings)
    with pytest.raises(InvalidResponseError):
        fetch_stations(session, settings)
    assert len(responses.calls) == 1


@responses.activate
def test_stations_http_500_then_200_retries_and_succeeds(settings, payload_station):
    # Arrange
    responses.add(responses.GET, URLSTATION, status=500)
    responses.add(responses.GET, URLSTATION, json=payload_station, status=200)
    session = build_session(settings)

    fast_fetch = fetch_stations.retry_with(wait=wait_none())

    # Act
    result = fast_fetch(session, settings)

    # Assert
    assert result == payload_station
    assert len(responses.calls) == 2


@responses.activate
def test_http_400_raises_invalid_request_without_retry(settings, payload):
    responses.add(
        responses.GET,
        URLLIVE,
        body="Invalid Request",
        status=400,
    )
    session = build_session(settings)
    # Act
    with pytest.raises(InvalidRequestError):
        fetch_liveboard(session, settings, FAKE_STATION)
    # Assert
    assert len(responses.calls) == 1


@responses.activate
def test_liveboard_http_500_then_200_retries_and_succeeds(settings, payload):
    # Arrange
    responses.add(responses.GET, URLLIVE, status=500)
    responses.add(responses.GET, URLLIVE, json=payload, status=200)
    session = build_session(settings)
    fast_fetch = fetch_liveboard.retry_with(wait=wait_none())
    # Act
    result = fast_fetch(session, settings, STATION)
    # Assert
    assert result == payload
    assert len(responses.calls) == 2


@responses.activate
def test_http_4x500_then_failed(settings, payload):
    # Arrange
    responses.add(responses.GET, URLLIVE, status=500)
    session = build_session(settings)
    fast_fetch = fetch_liveboard.retry_with(wait=wait_none())

    with pytest.raises(TransientAPIError):
        fast_fetch(session, settings, STATION)

    assert len(responses.calls) == MAX_ATTEMPTS
