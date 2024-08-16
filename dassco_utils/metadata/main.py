from .models import MetadataModel
import datetime


class MetadataHandler:

    def __init__(self, **kwargs):
        """
        Initialize the MetadataHandler object with the given kwargs.
        :param kwargs: metadata fields
        """
        try:
            copenhagen_tz = datetime.timezone(datetime.timedelta(hours=2))
            metadata_created_date = datetime.datetime.now(copenhagen_tz).replace(microsecond=0).isoformat()
            self.__metadata = MetadataModel(**kwargs, date_metadata_created=metadata_created_date)
        except Exception as e:
            raise e

    def metadata_to_json(self) -> str:
        """
        Returns a JSON representation of the metadata object.
        :return: JSON representation of the metadata object.
        """
        return self.__metadata.model_dump_json(indent=2)

    def metadata_to_dict(self) -> dict:
        """
        Returns a dictionary representation of the metadata object.
        :return: Dictionary representation of the metadata object.
        """
        return self.__metadata.model_dump()
