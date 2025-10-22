import os
from pydantic import BaseModel

class AnnouncementPayload(BaseModel):
    message: str
    channel_id: int = None if os.environ.get("CHANNEL_ID") is None else int(os.environ.get("CHANNEL_ID"))
    everyone: bool = False

class CreateEventPayload(BaseModel):
    guild_id: int
    channel_id: int | None = None
    name: str
    description: str
    start_time: str | None = None
    end_time: str | None = None
    entity_type: str = "external"
    location: str | None = None
    image_uri: str | None = None
 
class CheckAdminPayload(BaseModel):
    user_id: int
    guild_id: int
 
class VRCLoginPayload(BaseModel):
    email: str
    password: str
    
class VRCTwoFAPayload(BaseModel):
    code: str
    type: str