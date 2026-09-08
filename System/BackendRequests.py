from pydantic import BaseModel, Field


class SessionData(BaseModel):
    action: str
    content: dict = Field(default_factory=dict)


class BackendResponse(BaseModel):
    action: str
    content: dict | list


class BackendRequests:
    def build_responses(self, message):
        return BackendResponse(**message)
