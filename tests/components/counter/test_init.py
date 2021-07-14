"""The tests for the counter component."""
# pylint: disable=protected-access
import logging

import pytest

from homeassistant.components.counter import (
    ATTR_EDITABLE,
    ATTR_INITIAL,
    ATTR_MAXIMUM,
    ATTR_MINIMUM,
    ATTR_STEP,
    CONF_ICON,
    CONF_INITIAL,
    CONF_NAME,
    CONF_RESTORE,
    CONF_STEP,
    DEFAULT_INITIAL,
    DEFAULT_STEP,
    DOMAIN,
)
from homeassistant.const import ATTR_FRIENDLY_NAME, ATTR_ICON, ATTR_NAME
from homeassistant.core import Context, CoreState, State
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from tests.common import mock_restore_cache
from tests.components.counter.common import (
    async_decrement,
    async_increment,
    async_reset,
)

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
def storage_setup(hass, hass_storage):
    """Storage setup."""

    async def _storage(items=None, config=None):
        if items is None:
            hass_storage[DOMAIN] = {
                "key": DOMAIN,
                "version": 1,
                "data": {
                    "items": [
                        {
                            "id": "from_storage",
                            "initial": 10,
                            "name": "from storage",
                            "maximum": 100,
                            "minimum": 3,
                            "step": 2,
                            "restore": False,
                        }
                    ]
                },
            }
        else:
            hass_storage[DOMAIN] = {
                "key": DOMAIN,
                "version": 1,
                "data": {"items": items},
            }
        if config is None:
            config = {DOMAIN: {}}
        return await async_setup_component(hass, DOMAIN, config)

    return _storage


async def test_config(hass):
    """Test config."""
    invalid_configs = [None, 1, {}, {"name with space": None}]

    for cfg in invalid_configs:
        assert not await async_setup_component(hass, DOMAIN, {DOMAIN: cfg})


async def test_config_options(hass):
    """Test configuration options."""
    count_start = len(hass.states.async_entity_ids())

    _LOGGER.debug("ENTITIES @ start: %s", hass.states.async_entity_ids())

    config = {
        DOMAIN: {
            "test_1": {},
            "test_2": {
                CONF_NAME: "Hello World",
                CONF_ICON: "mdi:work",
                CONF_INITIAL: 10,
                CONF_RESTORE: False,
                CONF_STEP: 5,
            },
            "test_3": None,
        }
    }

    assert await async_setup_component(hass, "counter", config)
    await hass.async_block_till_done()

    _LOGGER.debug("ENTITIES: %s", hass.states.async_entity_ids())

    assert count_start + 3 == len(hass.states.async_entity_ids())
    await hass.async_block_till_done()

    state_1 = hass.states.get("counter.test_1")
    state_2 = hass.states.get("counter.test_2")
    state_3 = hass.states.get("counter.test_3")

    assert state_1 is not None
    assert state_2 is not None
    assert state_3 is not None

    assert int(state_1.state) == 0
    assert ATTR_ICON not in state_1.attributes
    assert ATTR_FRIENDLY_NAME not in state_1.attributes

    assert int(state_2.state) == 10
    assert state_2.attributes.get(ATTR_FRIENDLY_NAME) == "Hello World"
    assert state_2.attributes.get(ATTR_ICON) == "mdi:work"

    assert state_3.attributes.get(ATTR_INITIAL) == DEFAULT_INITIAL
    assert state_3.attributes.get(ATTR_STEP) == DEFAULT_STEP


async def test_methods(hass):
    """Test increment, decrement, and reset methods."""
    config = {DOMAIN: {"test_1": {}}}

    assert await async_setup_component(hass, "counter", config)

    entity_id = "counter.test_1"

    state = hass.states.get(entity_id)
    assert int(state.state) == 0

    async_increment(hass, entity_id)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert int(state.state) == 1

    async_increment(hass, entity_id)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert int(state.state) == 2

    async_decrement(hass, entity_id)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert int(state.state) == 1

    async_reset(hass, entity_id)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert int(state.state) == 0


async def test_methods_with_config(hass):
    """Test increment, decrement, and reset methods with configuration."""
    config = {
        DOMAIN: {"test": {CONF_NAME: "Hello World", CONF_INITIAL: 10, CONF_STEP: 5}}
    }

    assert await async_setup_component(hass, "counter", config)

    entity_id = "counter.test"

    state = hass.states.get(entity_id)
    assert int(state.state) == 10

    async_increment(hass, entity_id)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert int(state.state) == 15

    async_increment(hass, entity_id)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert int(state.state) == 20

    async_decrement(hass, entity_id)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert int(state.state) == 15


async def test_initial_state_overrules_restore_state(hass):
    """Ensure states are restored on startup."""
    mock_restore_cache(
        hass, (State("counter.test1", "11"), State("counter.test2", "-22"))
    )

    hass.state = CoreState.starting

    await async_setup_component(
        hass,
        DOMAIN,
        {
            DOMAIN: {
                "test1": {CONF_RESTORE: False},
                "test2": {CONF_INITIAL: 10, CONF_RESTORE: False},
            }
        },
    )

    state = hass.states.get("counter.test1")
    assert state
    assert int(state.state) == 0

    state = hass.states.get("counter.test2")
    assert state
    assert int(state.state) == 10


async def test_restore_state_overrules_initial_state(hass):
    """Ensure states are restored on startup."""

    attr = {"initial": 6, "minimum": 1, "maximum": 8, "step": 2}

    mock_restore_cache(
        hass,
        (
            State("counter.test1", "11"),
            State("counter.test2", "-22"),
            State("counter.test3", "5", attr),
        ),
    )

    hass.state = CoreState.starting

    await async_setup_component(
        hass, DOMAIN, {DOMAIN: {"test1": {}, "test2": {CONF_INITIAL: 10}, "test3": {}}}
    )

    state = hass.states.get("counter.test1")
    assert state
    assert int(state.state) == 11

    state = hass.states.get("counter.test2")
    assert state
    assert int(state.state) == -22

    state = hass.states.get("counter.test3")
    assert state
    assert int(state.state) == 5
    assert state.attributes.get("initial") == 6
    assert state.attributes.get("minimum") == 1
    assert state.attributes.get("maximum") == 8
    assert state.attributes.get("step") == 2


async def test_no_initial_state_and_no_restore_state(hass):
    """Ensure that entity is create without initial and restore feature."""
    hass.state = CoreState.starting

    await async_setup_component(hass, DOMAIN, {DOMAIN: {"test1": {CONF_STEP: 5}}})

    state = hass.states.get("counter.test1")
    assert state
    assert int(state.state) == 0


async def test_counter_context(hass, hass_admin_user):
    """Test that counter context works."""
    assert await async_setup_component(hass, "counter", {"counter": {"test": {}}})

    state = hass.states.get("counter.test")
    assert state is not None

    await hass.services.async_call(
        "counter",
        "increment",
        {"entity_id": state.entity_id},
        True,
        Context(user_id=hass_admin_user.id),
    )

    state2 = hass.states.get("counter.test")
    assert state2 is not None
    assert state.state != state2.state
    assert state2.context.user_id == hass_admin_user.id


async def test_counter_min(hass, hass_admin_user):
    """Test that min works."""
    assert await async_setup_component(
        hass, "counter", {"counter": {"test": {"minimum": "0", "initial": "0"}}}
    )

    state = hass.states.get("counter.test")
    assert state is not None
    assert state.state == "0"

    await hass.services.async_call(
        "counter",
        "decrement",
        {"entity_id": state.entity_id},
        True,
        Context(user_id=hass_admin_user.id),
    )

    state2 = hass.states.get("counter.test")
    assert state2 is not None
    assert state2.state == "0"

    await hass.services.async_call(
        "counter",
        "increment",
        {"entity_id": state.entity_id},
        True,
        Context(user_id=hass_admin_user.id),
    )

    state2 = hass.states.get("counter.test")
    assert state2 is not None
    assert state2.state == "1"


async def test_counter_max(hass, hass_admin_user):
    """Test that max works."""
    assert await async_setup_component(
        hass, "counter", {"counter": {"test": {"maximum": "0", "initial": "0"}}}
    )

    state = hass.states.get("counter.test")
    assert state is not None
    assert state.state == "0"

    await hass.services.async_call(
        "counter",
        "increment",
        {"entity_id": state.entity_id},
        True,
        Context(user_id=hass_admin_user.id),
    )

    state2 = hass.states.get("counter.test")
    assert state2 is not None
    assert state2.state == "0"

    await hass.services.async_call(
        "counter",
        "decrement",
        {"entity_id": state.entity_id},
        True,
        Context(user_id=hass_admin_user.id),
    )

    state2 = hass.states.get("counter.test")
    assert state2 is not None
    assert state2.state == "-1"


async def test_configure(hass, hass_admin_user):
    """Test that setting values through configure works."""
    assert await async_setup_component(
        hass, "counter", {"counter": {"test": {"maximum": "10", "initial": "10"}}}
    )

    state = hass.states.get("counter.test")
    assert state is not None
    assert state.state == "10"
    assert state.attributes.get("maximum") == 10

    # update max
    await hass.services.async_call(
        "counter",
        "configure",
        {"entity_id": state.entity_id, "maximum": 0},
        True,
        Context(user_id=hass_admin_user.id),
    )

    state = hass.states.get("counter.test")
    assert state is not None
    assert state.state == "0"
    assert state.attributes.get("maximum") == 0

    # disable max
    await hass.services.async_call(
        "counter",
        "configure",
        {"entity_id": state.entity_id, "maximum": None},
        True,
        Context(user_id=hass_admin_user.id),
    )

    state = hass.states.get("counter.test")
    assert state is not None
    assert state.state == "0"
    assert state.attributes.get("maximum") is None

    # update min
    assert state.attributes.get("minimum") is None
    await hass.services.async_call(
        "counter",
        "configure",
        {"entity_id": state.entity_id, "minimum": 5},
        True,
        Context(user_id=hass_admin_user.id),
    )

    state = hass.states.get("counter.test")
    assert state is not None
    assert state.state == "5"
    assert state.attributes.get("minimum") == 5

    # disable min
    await hass.services.async_call(
        "counter",
        "configure",
        {"entity_id": state.entity_id, "minimum": None},
        True,
        Context(user_id=hass_admin_user.id),
    )

    state = hass.states.get("counter.test")
    assert state is not None
    assert state.state == "5"
    assert state.attributes.get("minimum") is None

    # update step
    assert state.attributes.get("step") == 1
    await hass.services.async_call(
        "counter",
        "configure",
        {"entity_id": state.entity_id, "step": 3},
        True,
        Context(user_id=hass_admin_user.id),
    )

    state = hass.states.get("counter.test")
    assert state is not None
    assert state.state == "5"
    assert state.attributes.get("step") == 3

    # update value
    await hass.services.async_call(
        "counter",
        "configure",
        {"entity_id": state.entity_id, "value": 6},
        True,
        Context(user_id=hass_admin_user.id),
    )

    state = hass.states.get("counter.test")
    assert state is not None
    assert state.state == "6"

    # update initial
    await hass.services.async_call(
        "counter",
        "configure",
        {"entity_id": state.entity_id, "initial": 5},
        True,
        Context(user_id=hass_admin_user.id),
    )

    state = hass.states.get("counter.test")
    assert state is not None
    assert state.state == "6"
    assert state.attributes.get("initial") == 5

    # update all
    await hass.services.async_call(
        "counter",
        "configure",
        {
            "entity_id": state.entity_id,
            "step": 5,
            "minimum": 0,
            "maximum": 9,
            "value": 5,
            "initial": 6,
        },
        True,
        Context(user_id=hass_admin_user.id),
    )

    state = hass.states.get("counter.test")
    assert state is not None
    assert state.state == "5"
    assert state.attributes.get("step") == 5
    assert state.attributes.get("minimum") == 0
    assert state.attributes.get("maximum") == 9
    assert state.attributes.get("initial") == 6


async def test_load_from_storage(hass, storage_setup):
    """Test set up from storage."""
    assert await storage_setup()
    state = hass.states.get(f"{DOMAIN}.from_storage")
    assert int(state.state) == 10
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "from storage"
    assert state.attributes.get(ATTR_EDITABLE)


async def test_editable_state_attribute(hass, storage_setup):
    """Test editable attribute."""
    assert await storage_setup(
        config={
            DOMAIN: {
                "from_yaml": {
                    "minimum": 1,
                    "maximum": 10,
                    "initial": 5,
                    "step": 1,
                    "restore": False,
                }
            }
        }
    )

    state = hass.states.get(f"{DOMAIN}.from_storage")
    assert int(state.state) == 10
    assert state.attributes[ATTR_FRIENDLY_NAME] == "from storage"
    assert state.attributes[ATTR_EDITABLE] is True

    state = hass.states.get(f"{DOMAIN}.from_yaml")
    assert int(state.state) == 5
    assert state.attributes[ATTR_EDITABLE] is False


async def test_ws_list(hass, hass_ws_client, storage_setup):
    """Test listing via WS."""
    assert await storage_setup(
        config={
            DOMAIN: {
                "from_yaml": {
                    "minimum": 1,
                    "maximum": 10,
                    "initial": 5,
                    "step": 1,
                    "restore": False,
                }
            }
        }
    )

    client = await hass_ws_client(hass)

    await client.send_json({"id": 6, "type": f"{DOMAIN}/list"})
    resp = await client.receive_json()
    assert resp["success"]

    storage_ent = "from_storage"
    yaml_ent = "from_yaml"
    result = {item["id"]: item for item in resp["result"]}

    assert len(result) == 1
    assert storage_ent in result
    assert yaml_ent not in result
    assert result[storage_ent][ATTR_NAME] == "from storage"


async def test_ws_delete(hass, hass_ws_client, storage_setup):
    """Test WS delete cleans up entity registry."""
    assert await storage_setup()

    input_id = "from_storage"
    input_entity_id = f"{DOMAIN}.{input_id}"
    ent_reg = er.async_get(hass)

    state = hass.states.get(input_entity_id)
    assert state is not None
    assert ent_reg.async_get_entity_id(DOMAIN, DOMAIN, input_id) is not None

    client = await hass_ws_client(hass)

    await client.send_json(
        {"id": 6, "type": f"{DOMAIN}/delete", f"{DOMAIN}_id": f"{input_id}"}
    )
    resp = await client.receive_json()
    assert resp["success"]

    state = hass.states.get(input_entity_id)
    assert state is None
    assert ent_reg.async_get_entity_id(DOMAIN, DOMAIN, input_id) is None


async def test_update_min_max(hass, hass_ws_client, storage_setup):
    """Test updating min/max updates the state."""

    items = [
        {
            "id": "from_storage",
            "initial": 15,
            "name": "from storage",
            "maximum": 100,
            "minimum": 10,
            "step": 3,
            "restore": True,
        }
    ]
    assert await storage_setup(items)

    input_id = "from_storage"
    input_entity_id = f"{DOMAIN}.{input_id}"
    ent_reg = er.async_get(hass)

    state = hass.states.get(input_entity_id)
    assert state is not None
    assert int(state.state) == 15
    assert state.attributes[ATTR_MAXIMUM] == 100
    assert state.attributes[ATTR_MINIMUM] == 10
    assert state.attributes[ATTR_STEP] == 3
    assert ent_reg.async_get_entity_id(DOMAIN, DOMAIN, input_id) is not None

    client = await hass_ws_client(hass)

    await client.send_json(
        {
            "id": 6,
            "type": f"{DOMAIN}/update",
            f"{DOMAIN}_id": f"{input_id}",
            "minimum": 19,
        }
    )
    resp = await client.receive_json()
    assert resp["success"]

    state = hass.states.get(input_entity_id)
    assert int(state.state) == 19
    assert state.attributes[ATTR_MINIMUM] == 19
    assert state.attributes[ATTR_MAXIMUM] == 100
    assert state.attributes[ATTR_STEP] == 3

    await client.send_json(
        {
            "id": 7,
            "type": f"{DOMAIN}/update",
            f"{DOMAIN}_id": f"{input_id}",
            "maximum": 5,
            "minimum": 2,
            "step": 5,
        }
    )
    resp = await client.receive_json()
    assert resp["success"]

    state = hass.states.get(input_entity_id)
    assert int(state.state) == 5
    assert state.attributes[ATTR_MINIMUM] == 2
    assert state.attributes[ATTR_MAXIMUM] == 5
    assert state.attributes[ATTR_STEP] == 5

    await client.send_json(
        {
            "id": 8,
            "type": f"{DOMAIN}/update",
            f"{DOMAIN}_id": f"{input_id}",
            "maximum": None,
            "minimum": None,
            "step": 6,
        }
    )
    resp = await client.receive_json()
    assert resp["success"]

    state = hass.states.get(input_entity_id)
    assert int(state.state) == 5
    assert ATTR_MINIMUM not in state.attributes
    assert ATTR_MAXIMUM not in state.attributes
    assert state.attributes[ATTR_STEP] == 6


async def test_create(hass, hass_ws_client, storage_setup):
    """Test creating counter using WS."""

    items = []

    assert await storage_setup(items)

    counter_id = "new_counter"
    input_entity_id = f"{DOMAIN}.{counter_id}"
    ent_reg = er.async_get(hass)

    state = hass.states.get(input_entity_id)
    assert state is None
    assert ent_reg.async_get_entity_id(DOMAIN, DOMAIN, counter_id) is None

    client = await hass_ws_client(hass)

    await client.send_json({"id": 6, "type": f"{DOMAIN}/create", "name": "new counter"})
    resp = await client.receive_json()
    assert resp["success"]

    state = hass.states.get(input_entity_id)
    assert int(state.state) == 0
    assert ATTR_MINIMUM not in state.attributes
    assert ATTR_MAXIMUM not in state.attributes
    assert state.attributes[ATTR_STEP] == 1
