from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum


class FileFormat(str, Enum):
    TIF = "tif"
    JPEG = "jpeg"
    RAF = "raf"


class PayloadType(str, Enum):
    IMAGE = "image"
    CT_SCAN = "ct scan"
    SURFACE_SCAN = "surface scan"
    DOCUMENT = "document"


class PreparationType(str, Enum):
    SHEET = "sheet"
    PINNED = "pinned"
    DRY = "dry"
    SLIDE = "slide"


class Status(str, Enum):
    WORKING_COPY = "working copy"
    ARCHIVE = "archive"
    FOR_PROCESSING = "for processing"
    BEING_PROCESSED = "being processed"
    PROCESSING_HALTED = "processing halted"
    ISSUE_WITH_MEDIA = "issue with media"
    ISSUE_WITH_METADATA = "issue with metadata"
    FOR_DELETION = "for deletion"


class MetadataModel(BaseModel):
    asset_created_by: Optional[str] = None
    asset_deleted_by: Optional[str] = None
    asset_guid: str
    asset_pid: Optional[str] = None
    asset_subject: Optional[str] = None
    date_asset_taken: datetime
    asset_updated_by: Optional[str] = None
    audited: bool = False
    audited_by: Optional[str] = None
    audited_date: Optional[datetime] = None
    barcode: List[str] = []
    collection: str
    date_asset_created: Optional[datetime] = None
    date_asset_deleted: Optional[datetime] = None
    date_asset_finalised: Optional[datetime] = None
    date_asset_updated: Optional[datetime] = None
    date_metadata_created: datetime
    date_metadata_updated: Optional[datetime] = None
    date_metadata_uploaded: Optional[datetime] = None
    digitiser: str
    external_publisher: List[str] = []
    file_format: FileFormat
    funding: str
    institution: str
    metadata_created_by: Optional[str] = None
    metadata_updated_by: Optional[str] = None
    metadata_uploaded_by: Optional[str] = None
    multispecimen: bool = False
    parent_guid: Optional[str] = None
    payload_type: PayloadType
    pipeline_name: str
    preparation_type: PreparationType
    pushed_to_specify_date: Optional[str] = None
    restricted_access: List[str] = []
    specimen_pid: Optional[str] = None
    status: Optional[Status] = None
    tags: Dict[str, str] = Field(default_factory=lambda: {"metadataTemplate": "v2_1_0"})
    workstation_name: str
