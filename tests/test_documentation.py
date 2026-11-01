"""Installation documentation: the collector and its websocket command."""

import pytest
from homeassistant.core import HomeAssistant

from custom_components.enocean_eltako.documentation import VERSION, collect

from .test_devices import BASE, _push, _settle, _subentry, gateway  # noqa: F401

pytestmark = pytest.mark.usefixtures("socket_enabled")


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "switch",
                "05-10-A2-C1",
                "Licht Flur",
                senders=[
                    {"profile": "central", "sender_id": "FF-B7-44-91"},
                    {"profile": "rocker", "sender_id": "FF-B7-44-92"},
                ],
                rocker_on_button="a0",
                rocker_off_button="a1",
                wall_switch="05-10-AA-01",
                wall_on_button="a0",
                wall_off_button="a1",
            ),
            _subentry("meter", "05-00-00-12", "Waschmaschine"),
        ]
    ],
    indirect=True,
)
async def test_collect_describes_gateway_devices_senders_and_pool(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
) -> None:
    entry, server = gateway
    flur = next(d for d in entry.runtime_data.devices.values() if d.subentry.title == "Licht Flur")
    flur.last_sender_test["central"] = "confirmed"
    pool = entry.runtime_data.senders.pool
    pool.assign(0xFFB74491, "device:05-10-A2-C1:central")
    pool.assign(0xFFB74495, "device:gone:central")
    pool.release(0xFFB74495)  # a deleted device: blocked until the teach-out is confirmed
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "enocean_eltako/documentation"})
    reply = await client.receive_json()
    assert reply["success"]
    doc = reply["result"]
    assert doc == {**collect(hass), "generated": doc["generated"]}
    assert doc["version"] == VERSION

    (shown,) = doc["gateways"]
    assert shown["entry_id"] == entry.entry_id and shown["base_id"] == BASE
    assert shown["model"] == "fam_usb"
    names = [d["name"] for d in shown["devices"]]
    assert names == ["Licht Flur", "Waschmaschine"]

    flur_row, meter_row = shown["devices"]
    assert flur_row["id"] == "05-10-A2-C1" and flur_row["virtual"] is False
    assert flur_row["wall_switch"] == {"id": "05-10-AA-01", "on": "a0", "off": "a1"}
    senders = {s["profile"]: s for s in flur_row["senders"]}
    assert senders["central"]["id"] == "FF-B7-44-91"
    assert senders["central"]["test"] == "confirmed" and senders["rocker"]["test"] is None
    assert meter_row["senders"] == [] and meter_row["wall_switch"] is None
    assert meter_row["eep"] is not None

    (pool,) = shown["pools"]
    assert pool["kind"] == "radio" and pool["start"] == "FF-B7-44-81"
    owned = {s["id"]: s for s in pool["senders"]}
    assert owned["FF-B7-44-91"]["device"] == "Licht Flur"
    assert owned["FF-B7-44-91"]["state"] == "assigned"
    assert owned["FF-B7-44-95"] == {
        "id": "FF-B7-44-95",
        "device": None,
        "profile": "central",
        "state": "blocked",
    }
    assert shown["hidden_senders"] == []
