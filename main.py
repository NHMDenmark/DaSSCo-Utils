from dassco_utils.guid import create_guid, create_derivative_guid
from dassco_utils.metadata import MetadataHandler
import datetime

time = "2024-08-15T15:11:24+02:00"

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

guid = create_guid(mapping, '2024-08-08T12:27:21+02:00', 'test_inst', 'test_collect', 'test_work')

print(guid)
print(create_derivative_guid(guid, 7))
"""
data = {
    'asset_guid': create_guid(mapping, '2024-08-08T12:27:21+02:00', 'NHMD', 'Entomology', 'WORKHERB0001'),
    'date_asset_taken': '2024-08-08T12:27:21+02:00',
    'collection': 'Entomology',
    'digitiser': 'John Doe',
    'file_format': 'tif',
    'payload_type': 'image',
    'pipeline_name': 'PIPEHERB0001',
    'preparation_type': 'sheet',
    'workstation_name': 'WORKHERB0001',
    'institution': 'NHMD',
    'funding': 'DaSSCo',
}

handler = MetadataHandler(**data)

print(handler.metadata_to_json())


"""
