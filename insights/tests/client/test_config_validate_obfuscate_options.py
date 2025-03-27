import pytest

try:
    from unittest.mock import patch
except Exception:
    from mock import patch

from insights.client.config import InsightsConfig


@pytest.mark.parametrize(
    ("obfuscate", "obfuscate_hostname", "obfuscate_opt", "expected_opt"),
    [
        (True, True, [], ['ipv4', 'hostname']),
        (True, False, [], ['ipv4']),
        (False, False, [], []),
        (False, False, ['ipv6', 'hostname', 'ipv4'], ['hostname', 'ipv4', 'ipv6']),
        (False, False, ['ipv4', 'ipv6', 'hostname', 'mac'], ['hostname', 'ipv4', 'ipv6', 'mac']),
    ],
)
def test_validate_obfuscate_options_good(
    obfuscate, obfuscate_hostname, obfuscate_opt, expected_opt
):
    c = InsightsConfig(
        obfuscate=obfuscate, obfuscate_hostname=obfuscate_hostname, obfuscate_opt=obfuscate_opt
    )
    assert c.obfuscate_opt == expected_opt
    assert c.obfuscate is None
    assert c.obfuscate_hostname is None


@patch('insights.client.config.sys.stdout.write')
def test_validate_obfuscate_options_conflict(sys_write):
    with pytest.raises(ValueError) as ve:
        InsightsConfig(obfuscate=False, obfuscate_hostname=True, _print_errors=True)
    assert 'Option `obfuscate_hostname` requires `obfuscate`' in str(ve.value)
    sys_write.assert_called_once_with(
        'WARNING: `obfuscate` and `obfuscate_hostname` are deprecated, please use `obfuscate_opt` instead.\n'
    )

    with pytest.raises(ValueError) as ve:
        InsightsConfig(obfuscate=True, obfuscate_opt=['ipv4'], _print_errors=True)
    assert 'Conflicting options: `obfuscate_opt` and `obfuscate`' in str(ve.value)


@patch('insights.client.config.sys.stdout.write')
def test_validate_obfuscate_options_invalid(sys_write):
    InsightsConfig(obfuscate_opt=['mac', 'abc', 'ipv4'], _print_errors=True)
    sys_write.assert_called_once_with(
        'WARNING: ignoring invalid obfuscate options: `abc`, using: "obfuscate_opt=ipv4,mac"\n'
    )
