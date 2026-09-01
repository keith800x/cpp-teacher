#include "RuntimeTraceParser.h"

#include <sstream>
#include <string>
#include <vector>

namespace
{
std::vector<std::string> split(
    const std::string& value,
    char delimiter
)
{
    std::vector<std::string> parts;
    std::stringstream stream(value);
    std::string part;

    while (std::getline(stream, part, delimiter))
    {
        parts.push_back(part);
    }

    return parts;
}

bool parseType(
    const std::string& name,
    TraceEventType& type
)
{
    if (name == "ENTER_SCOPE")
    {
        type = TraceEventType::EnterScope;
        return true;
    }

    if (name == "EXIT_SCOPE")
    {
        type = TraceEventType::ExitScope;
        return true;
    }

    if (name == "CREATE_OBJECT")
    {
        type = TraceEventType::CreateObject;
        return true;
    }

    if (name == "CREATE_VALUE")
    {
        type = TraceEventType::CreateValue;
        return true;
    }

    if (name == "BIND_ALIAS")
    {
        type = TraceEventType::BindAlias;
        return true;
    }

    if (name == "WRITE_VALUE")
    {
        type = TraceEventType::WriteValue;
        return true;
    }


    if (name == "ALLOCATE_RESOURCE")
    {
        type = TraceEventType::AllocateResource;
        return true;
    }

    if (name == "BIND_POINTER")
    {
        type = TraceEventType::BindPointer;
        return true;
    }

    if (name == "COPY_RESOURCE")
    {
        type = TraceEventType::CopyResource;
        return true;
    }

    if (name == "MOVE_RESOURCE")
    {
        type = TraceEventType::MoveResource;
        return true;
    }

    if (name == "SET_NULL")
    {
        type = TraceEventType::SetNull;
        return true;
    }

    if (name == "DESTROY_BEGIN")
    {
        type = TraceEventType::DestroyBegin;
        return true;
    }

    if (name == "DESTROY_END")
    {
        type = TraceEventType::DestroyEnd;
        return true;
    }

    if (name == "DESTROY_OBJECT")
    {
        type = TraceEventType::DestroyObject;
        return true;
    }

    if (name == "FREE_RESOURCE")
    {
        type = TraceEventType::FreeResource;
        return true;
    }

    if (name == "WARNING")
    {
        type = TraceEventType::Warning;
        return true;
    }

    return false;
}
}

SemanticTrace RuntimeTraceParser::parse(
    const std::string& stderrText
) const
{
    SemanticTrace trace;

    std::stringstream stream(stderrText);
    std::string line;

    while (std::getline(stream, line))
    {
        if (line.rfind("TRACE|", 0) != 0)
        {
            continue;
        }

        const std::vector<std::string> parts =
            split(line, '|');

        if (parts.size() < 4)
        {
            continue;
        }

        TraceEventType type;

        if (!parseType(parts[1], type))
        {
            continue;
        }

        std::string detail = parts[3];

        for (std::size_t i = 4; i < parts.size(); ++i)
        {
            detail += "|" + parts[i];
        }

        trace.events.push_back({
            type,
            parts[2],
            detail
        });
    }

    return trace;
}
