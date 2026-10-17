"""Leak-Lookup module must not use an embedded fallback credential."""
from unittest.mock import Mock
from urllib.parse import parse_qs
from types import SimpleNamespace

import pytest

from modules.sfp_citadel import sfp_citadel


@pytest.mark.parametrize("missing_key", ["", "  "])
def test_missing_api_key_stops_before_external_request(missing_key):
    module = sfp_citadel()
    module.opts = dict(module.opts, api_key=missing_key, _useragent="stage3-test")
    module.sf = Mock()
    module.sf.fetchUrl.return_value = {"code": "200", "content": '{"error":"false","message":[]}'}
    module.error = Mock()

    result = module.queryEmail("alice@example.invalid")

    assert result is None
    assert module.errorState is True
    module.error.assert_called_once_with("API 密钥未配置")
    module.sf.fetchUrl.assert_not_called()


def test_configured_test_key_is_used_only_in_mocked_request():
    placeholder = "STAGE3_TEST_PLACEHOLDER_ONLY"
    module = sfp_citadel()
    module.opts = dict(module.opts, api_key=placeholder, _useragent="stage3-test")
    module.sf = Mock()
    module.sf.fetchUrl.return_value = {"code": "200", "content": '{"error":"false","message":[]}'}

    result = module.queryEmail("alice@example.invalid")

    assert result == {"error": "false", "message": []}
    module.sf.fetchUrl.assert_called_once()
    assert parse_qs(module.sf.fetchUrl.call_args.kwargs["postData"])["key"] == [placeholder]


def test_transport_error_does_not_expose_configured_key_in_logs_or_exception():
    placeholder = "STAGE3_TEST_PLACEHOLDER_ONLY"
    module = sfp_citadel()
    module.opts = dict(module.opts, api_key=placeholder, _useragent="stage3-test")
    module.sf = Mock()
    module.sf.fetchUrl.side_effect = RuntimeError("transport failed with credential " + placeholder)
    module.error = Mock()
    module.debug = Mock()

    assert module.queryEmail("alice@example.invalid") is None
    assert module.errorState is True
    assert placeholder not in repr(module.error.call_args_list)
    assert placeholder not in repr(module.debug.call_args_list)


def test_remote_error_echoing_key_is_not_written_to_module_logs():
    placeholder = "STAGE3_TEST_PLACEHOLDER_ONLY"
    module = sfp_citadel()
    module.opts = dict(module.opts, api_key=placeholder, _useragent="stage3-test")
    module.results = {}
    module.errorState = False
    module.queryEmail = Mock(return_value={"error": "true", "message": "MISSING API " + placeholder})
    module.error = Mock()
    module.debug = Mock()
    event = SimpleNamespace(eventType="EMAILADDR", module="stage3-test", data="alice@example.invalid")

    module.handleEvent(event)

    assert module.errorState is True
    assert placeholder not in repr(module.error.call_args_list)
    assert placeholder not in repr(module.debug.call_args_list)
