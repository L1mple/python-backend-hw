from dataclasses import dataclass


@dataclass(slots=True)
class PokemonInfo:
    name: str
    published: bool


@dataclass(slots=True)
class PokemonEntity:
    id: int
    info: PokemonInfo


@dataclass(slots=True)
class PatchPokemonInfo:
    name: str | None = None
    published: bool | None = None
