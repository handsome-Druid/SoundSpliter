from pydantic import BaseModel, Field


class V2(BaseModel):
    left: str | None = None
    right: str | None = None
    source: str | None = None
    volume: str | None = None
    left_latency_ms: int = Field(default=0, ge=0)
    right_latency_ms: int = Field(default=0, ge=0)
    left_buffer_time_ms: int = Field(default=30, ge=0)
    right_buffer_time_ms: int = Field(default=30, ge=0)
    source_buffer_time_ms: int = Field(default=20, ge=0)
