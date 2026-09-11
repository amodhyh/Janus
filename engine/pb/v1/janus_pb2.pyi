from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Action(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACTION_UNSPECIFIED: _ClassVar[Action]
    ACTION_ALLOW: _ClassVar[Action]
    ACTION_DENY: _ClassVar[Action]
    ACTION_MUTATE: _ClassVar[Action]
ACTION_UNSPECIFIED: Action
ACTION_ALLOW: Action
ACTION_DENY: Action
ACTION_MUTATE: Action

class InspectionRequest(_message.Message):
    __slots__ = ("request_id", "raw_prompt")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    RAW_PROMPT_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    raw_prompt: str
    def __init__(self, request_id: _Optional[str] = ..., raw_prompt: _Optional[str] = ...) -> None: ...

class InspectionResponse(_message.Message):
    __slots__ = ("action", "mutated_prompt", "reason")
    ACTION_FIELD_NUMBER: _ClassVar[int]
    MUTATED_PROMPT_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    action: Action
    mutated_prompt: str
    reason: str
    def __init__(self, action: _Optional[_Union[Action, str]] = ..., mutated_prompt: _Optional[str] = ..., reason: _Optional[str] = ...) -> None: ...
