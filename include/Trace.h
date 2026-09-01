#pragma once

#include <string>
#include <vector>

enum class TraceEventType
{
    EnterScope,
    ExitScope,
    CreateObject,
    CreateValue,
    BindAlias,
    WriteValue,
    AllocateResource,
    BindPointer,
    CopyResource,
    MoveResource,
    SetNull,
    DestroyBegin,
    DestroyEnd,
    DestroyObject,
    FreeResource,
    Warning
};

struct TraceEvent
{
    TraceEventType type;
    std::string subject;
    std::string detail;
};

struct SemanticTrace
{
    std::vector<TraceEvent> events;
};

std::string toString(TraceEventType type);
