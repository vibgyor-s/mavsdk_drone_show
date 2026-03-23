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
