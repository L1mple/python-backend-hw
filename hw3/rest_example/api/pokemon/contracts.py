from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from hw2.rest_example.store.models import (
    PatchPokemonInfo,
    PokemonEntity,
    PokemonInfo,
)


class PokemonResponse(BaseModel):
    id: int
    name: str
    published: bool

    @staticmethod
    def from_entity(entity: PokemonEntity) -> PokemonResponse:
        return PokemonResponse(
            id=entity.id,
            name=entity.info.name,
            published=entity.info.published,
        )


class PokemonRequest(BaseModel):
    name: str
    published: bool

    def as_pokemon_info(self) -> PokemonInfo:
        return PokemonInfo(name=self.name, published=self.published)


class PatchPokemonRequest(BaseModel):
    name: str | None = None
    published: bool | None = None

    model_config = ConfigDict(extra="forbid")

    def as_patch_pokemon_info(self) -> PatchPokemonInfo:
        return PatchPokemonInfo(name=self.name, published=self.published)
