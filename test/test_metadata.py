from dassco_utils.metadata import MetadataHandler
from freezegun import freeze_time
import json


@freeze_time("2024-08-16T08:44:57+02:00")
def test_create_json_metadata():

    data = {
        'asset_guid': '7e8-8-08-0c-1b-15-2-003-04-000-0d4437',
        'date_asset_taken': '2024-08-16T08:44:57+02:00',
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

    metadata_json = handler.metadata_to_json()

    expected_json_output = json.dumps({
        "asset_created_by": None,
        "asset_deleted_by": None,
        "asset_guid": "7e8-8-08-0c-1b-15-2-003-04-000-0d4437",
        "asset_pid": None,
        "asset_subject": None,
        "date_asset_taken": "2024-08-16T08:44:57+02:00",
        "asset_updated_by": None,
        "audited": False,
        "audited_by": None,
        "audited_date": None,
        "barcode": [],
        "collection": "Entomology",
        "date_asset_created": None,
        "date_asset_deleted": None,
        "date_asset_finalised": None,
        "date_asset_updated": None,
        "date_metadata_created": "2024-08-16T08:44:57+02:00",
        "date_metadata_updated": None,
        "date_metadata_uploaded": None,
        "digitiser": "John Doe",
        "external_publisher": [],
        "file_format": "tif",
        "funding": "DaSSCo",
        "institution": "NHMD",
        "metadata_created_by": None,
        "metadata_updated_by": None,
        "metadata_uploaded_by": None,
        "multispecimen": False,
        "parent_guid": None,
        "payload_type": "image",
        "pipeline_name": "PIPEHERB0001",
        "preparation_type": "sheet",
        "pushed_to_specify_date": None,
        "restricted_access": [],
        "specimen_pid": None,
        "status": None,
        "tags": {"metadataTemplate": "v2_1_0"},
        "workstation_name": "WORKHERB0001"
    }, indent=2)

    assert json.loads(metadata_json) == json.loads(expected_json_output)
