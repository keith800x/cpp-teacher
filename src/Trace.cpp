#include "Trace.h"

std::string toString(TraceEventType type)
{
    switch (type)
    {
        case TraceEventType::EnterScope: return "ENTER_SCOPE";
        case TraceEventType::ExitScope: return "EXIT_SCOPE";
        case TraceEventType::CreateObject: return "CREATE_OBJECT";
        case TraceEventType::CreateValue: return "CREATE_VALUE";
        case TraceEventType::BindAlias: return "BIND_ALIAS";
        case TraceEventType::WriteValue: return "WRITE_VALUE";
        case TraceEventType::AllocateResource: return "ALLOCATE_RESOURCE";
        case TraceEventType::BindPointer: return "BIND_POINTER";
        case TraceEventType::CopyResource: return "COPY_RESOURCE";
        case TraceEventType::MoveResource: return "MOVE_RESOURCE";
        case TraceEventType::SetNull: return "SET_NULL";
        case TraceEventType::DestroyBegin: return "DESTROY_BEGIN";
        case TraceEventType::DestroyEnd: return "DESTROY_END";
        case TraceEventType::DestroyObject: return "DESTROY_OBJECT";
        case TraceEventType::FreeResource: return "FREE_RESOURCE";
        case TraceEventType::Warning: return "WARNING";
    }

    return "UNKNOWN";
}
