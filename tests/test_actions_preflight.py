from types import SimpleNamespace

import pytest

import actions


class _DummyTelemetry:
    def __init__(self, samples):
        self._samples = samples

    async def health(self):
        for sample in self._samples:
            yield sample


class _DummyDrone:
    def __init__(self, samples):
        self.telemetry = _DummyTelemetry(samples)


@pytest.mark.asyncio
async def test_ensure_ready_for_flight_uses_local_home_fallback(mocker):
    mocker.patch(
        "actions._get_local_drone_state_snapshot",
        return_value={"home_position_set": True},
    )

    drone = _DummyDrone([
        SimpleNamespace(is_global_position_ok=True, is_home_position_ok=False),
    ])

    assert await actions.ensure_ready_for_flight(drone, timeout=1) is True


@pytest.mark.asyncio
async def test_wait_until_relative_altitude_uses_local_fallback_after_mavsdk_timeout(mocker):
    wait_mock = mocker.patch(
        "actions.wait_for_telemetry_condition",
        new=mocker.AsyncMock(side_effect=TimeoutError("mavsdk timeout")),
    )
    mocker.patch("actions._get_local_relative_altitude_snapshot", return_value=8.6)

    result = await actions.wait_until_relative_altitude(object(), 8.0, timeout=1)

    wait_mock.assert_awaited_once()
    assert result == 8.6


@pytest.mark.asyncio
async def test_wait_until_relative_altitude_raises_when_fallback_is_still_below_target(mocker):
    mocker.patch(
        "actions.wait_for_telemetry_condition",
        new=mocker.AsyncMock(side_effect=TimeoutError("mavsdk timeout")),
    )
    mocker.patch("actions._get_local_relative_altitude_snapshot", return_value=4.2)

    with pytest.raises(TimeoutError, match="mavsdk timeout"):
        await actions.wait_until_relative_altitude(object(), 8.0, timeout=1)
