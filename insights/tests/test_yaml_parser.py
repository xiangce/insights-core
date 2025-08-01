import datetime
import pytest

from insights.core import YAMLParser
from insights.core.exceptions import ParseException, SkipComponent
from insights.tests import context_wrap


bi_conf_content = """
{"remote_branch": -1, "remote_leaf": -1}
""".strip()

yaml_test_strings = {
    """
type:        Acquisition
date:        2019-07-09
""": {
        'type': 'Acquisition',
        'date': datetime.date(2019, 7, 9),
    },
    """
- Hesperiidae
- Papilionidae
- Apatelodidae
- Epiplemidae
""": [
        'Hesperiidae',
        'Papilionidae',
        'Apatelodidae',
        'Epiplemidae',
    ],
}

yaml_content_with_extra_lines = """
test=abc
---
server:
  hostname: abc
""".strip()

empty_yaml_content = """
---
# This YAML file is empty
""".strip()

wrong_yaml_content = """
"unbalanced blackets: ]["
""".strip()


class FakeYamlParser(YAMLParser):
    """Class for parsing the content of ``branch_info``."""

    pass


class MyYamlParser(YAMLParser):
    ignore_lines = ['test=']


def test_yaml_parser_success():
    for ymlstr in yaml_test_strings:
        ctx = context_wrap(ymlstr)
        assert FakeYamlParser(ctx).data == yaml_test_strings[ymlstr]


def test_yaml_parser_success_skip_lines():
    ctx = context_wrap(yaml_content_with_extra_lines)
    assert MyYamlParser(ctx).get('server').get('hostname') == 'abc'


def test_yaml_parser_failure():
    ctx = context_wrap("boom /")
    with pytest.raises(ParseException) as ex:
        FakeYamlParser(ctx)

    assert "FakeYamlParser" in ex.value.args[0]


def test_settings_yml():
    ctx = context_wrap(bi_conf_content)
    ctx.content = bi_conf_content
    result = FakeYamlParser(ctx)
    assert result.data['remote_branch'] == -1
    assert result.data['remote_leaf'] == -1


def test_settings_yml_list():
    ctx = context_wrap(bi_conf_content)
    result = FakeYamlParser(ctx)
    assert result.data['remote_branch'] == -1
    assert result.data['remote_leaf'] == -1


def test_empty_content():
    ctx = context_wrap(empty_yaml_content)
    with pytest.raises(SkipComponent) as ex:
        FakeYamlParser(ctx)

    assert "There is no data" in ex.value.args[0]


def test_yaml_parser_with_equal_value():
    ctx = context_wrap("key: =")
    assert FakeYamlParser(ctx).data == {"key": "="}

    ctx = context_wrap("key: value")
    assert FakeYamlParser(ctx).data == {"key": "value"}
