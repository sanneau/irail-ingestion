import pytest
import responses
from tenacity import wait_none

from irail_ingestion.client import MAX_ATTEMPTS, build_session, fetch_liveboard
from irail_ingestion.exceptions import InvalidRequestError, TransientAPIError

URL = "https://api.irail.be/v1/liveboard"
STATION = "BE.NMBS.008813003"
FAKE_STATION = "Atlantis"


@responses.activate
def test_fetch_liveboard_returns_the_payload(settings, payload):
    # Arrange : « si quelqu'un fait un GET sur URL, réponds 200 avec ce JSON »
    responses.add(responses.GET, URL, json=payload, status=200)
    session = build_session(settings)

    # Act
    result = fetch_liveboard(session, settings, STATION)

    # Assert
    assert result == payload
    assert len(responses.calls) == 1
    assert responses.calls[0].request.headers["User-Agent"] == "irail-test"


@responses.activate
def test_http_400_raises_invalid_request_without_retry(settings, payload):
    responses.add(
        responses.GET,
        URL,
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
def test_http_500_then_200_retries_and_succeeds(settings, payload):
    # Arrange
    responses.add(responses.GET, URL, status=500)
    responses.add(responses.GET, URL, json=payload, status=200)
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
    responses.add(responses.GET, URL, status=500)
    session = build_session(settings)
    fast_fetch = fetch_liveboard.retry_with(wait=wait_none())

    with pytest.raises(TransientAPIError):
        fast_fetch(session, settings, STATION)

    assert len(responses.calls) == MAX_ATTEMPTS
