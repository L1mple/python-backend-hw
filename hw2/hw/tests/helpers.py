from polyfactory.factories.pydantic_factory import ModelFactory

from shop_api.models import BaseItem

class BaseItemFactory(ModelFactory[BaseItem]):
    __model__ = BaseItem
