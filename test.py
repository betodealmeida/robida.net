from pydantic import BaseModel, model_validator


class Foo(BaseModel):
    a: int
    b: str

    @model_validator(mode="before")
    @classmethod
    def pre_root(cls, values):
        print(values)
        return values


print(Foo("foo"))
