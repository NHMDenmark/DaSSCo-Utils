from dassco_utils.guid import create_guid, create_derivative_guid
from unittest.mock import patch
import pytest


def test_create_guid():
    mapping = {
        "institution": {
            "test_inst": 2,
        },
        "collection": {
            "test_collect": 3,
        },
        "workstation": {
            "test_work": 4,
        },
    }

    date = "2024-08-08T12:27:21+02:00"

    expected_components = [
        '7e8',
        '8',
        '08',
        '0c',
        '1b',
        '15',
        '2',
        '003',
        '04',
        '000',
        '01e240'
    ]

    # Mock randint
    with patch('random.randint', return_value=123456):
        guid = create_guid(mapping, date, "test_inst", "test_collect", "test_work")
        expected_guid = '-'.join(expected_components)
        assert guid == expected_guid


def test_create_derivative_guid():
    parent_guid = "7e8-8-08-0c-1b-15-2-003-04-000-0d4437"
    expected_derivative_guid = "7e8-8-08-0c-1b-15-2-003-04-007-0d4437-00000"

    derivative_guid = create_derivative_guid(parent_guid, 7)

    assert expected_derivative_guid == derivative_guid


def test_create_derivative_guid_already_derived():
    derived_guid = "7e8-8-08-0c-1b-15-2-003-04-007-0d4437-00000"

    with pytest.raises(ValueError):
        create_derivative_guid(derived_guid, 5)




