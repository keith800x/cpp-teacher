#include "MemoryStateBuilder.h"

#include <algorithm>
#include <map>
#include <string>

namespace
{
std::string objectNameFromPointer(
    const std::string& pointerName
)
{
    const std::size_t dot =
        pointerName.find('.');

    if (dot == std::string::npos)
    {
        return pointerName;
    }

    return pointerName.substr(0, dot);
}

std::string fieldNameFromPointer(
    const std::string& pointerName
)
{
    const std::size_t dot =
        pointerName.find('.');

    if (dot == std::string::npos ||
        dot + 1 >= pointerName.size())
    {
        return {};
    }

    return pointerName.substr(dot + 1);
}

std::string trim(std::string value)
{
    while (!value.empty() &&
           (value.front() == ' ' ||
            value.front() == '\t'))
    {
        value.erase(value.begin());
    }

    while (!value.empty() &&
           (value.back() == ' ' ||
            value.back() == '\t'))
    {
        value.pop_back();
    }

    return value;
}

std::pair<std::string, std::string>
parseArrow(const std::string& detail)
{
    const std::size_t arrow =
        detail.find("->");

    if (arrow == std::string::npos)
    {
        return {};
    }

    std::string destination =
        trim(detail.substr(arrow + 2));

    const std::size_t metadata =
        destination.find('|');

    if (metadata != std::string::npos)
    {
        destination =
            trim(
                destination.substr(
                    0,
                    metadata
                )
            );
    }

    return {
        trim(detail.substr(0, arrow)),
        destination
    };
}


std::string extractDetailValue(
    const std::string& detail,
    const std::string& key
)
{
    const std::string prefix = key + "=";
    const std::size_t start = detail.find(prefix);

    if (start == std::string::npos)
    {
        return {};
    }

    const std::size_t valueStart =
        start + prefix.size();

    const std::size_t end =
        detail.find('|', valueStart);

    if (end == std::string::npos)
    {
        return detail.substr(valueStart);
    }

    return detail.substr(
        valueStart,
        end - valueStart
    );
}

std::string parseResourceValue(
    const std::string& detail
)
{
    constexpr const char* prefix = "value=";

    const std::size_t pos =
        detail.find(prefix);

    if (pos == std::string::npos)
    {
        return {};
    }

    return detail.substr(
        pos + std::string(prefix).size()
    );
}

std::vector<StackObjectState> copyObjects(
    const std::map<std::string, StackObjectState>& objects
)
{
    std::vector<StackObjectState> result;

    for (const auto& [name, state] : objects)
    {
        result.push_back(state);
    }

    return result;
}


std::vector<StackValueState> copyStackValues(
    const std::map<std::string, StackValueState>& values
)
{
    std::vector<StackValueState> result;

    for (const auto& [name, state] : values)
    {
        result.push_back(state);
    }

    return result;
}

std::vector<AliasState> copyAliases(
    const std::map<std::string, AliasState>& aliases
)
{
    std::vector<AliasState> result;

    for (const auto& [name, state] : aliases)
    {
        result.push_back(state);
    }

    return result;
}

std::vector<HeapResourceState> copyResources(
    const std::map<std::string, HeapResourceState>& resources
)
{
    std::vector<HeapResourceState> result;

    for (const auto& [id, state] : resources)
    {
        result.push_back(state);
    }

    return result;
}
}

MemoryTimeline MemoryStateBuilder::build(
    const SemanticTrace& trace
) const
{
    MemoryTimeline timeline;

    std::map<std::string, StackObjectState> objects;
    std::map<std::string, StackValueState> stackValues;
    std::map<std::string, AliasState> aliases;
    std::map<std::string, HeapResourceState> resources;
    std::vector<std::string> activeScopes;

    int step = 1;

    for (const TraceEvent& event : trace.events)
    {
        switch (event.type)
        {
            case TraceEventType::EnterScope:
            {
                activeScopes.push_back(event.subject);
                break;
            }

            case TraceEventType::ExitScope:
            {
                for (auto& [name, value] : stackValues)
                {
                    if (value.scopeName == event.subject)
                    {
                        value.alive = false;
                    }
                }

                for (auto& [name, alias] : aliases)
                {
                    if (alias.scopeName == event.subject)
                    {
                        alias.alive = false;
                    }
                }

                if (!activeScopes.empty() &&
                    activeScopes.back() == event.subject)
                {
                    activeScopes.pop_back();
                }

                break;
            }

            case TraceEventType::CreateObject:
            {
                StackObjectState object;
                object.name = event.subject;
                object.alive = true;
                object.destroying = false;

                if (!activeScopes.empty())
                {
                    object.scopeName = activeScopes.back();
                }

                const std::string eventTypeName =
                    extractDetailValue(
                        event.detail,
                        "type"
                    );

                if (!eventTypeName.empty())
                {
                    object.typeName =
                        eventTypeName;
                }

                const std::string pointerField =
                    extractDetailValue(
                        event.detail,
                        "pointer"
                    );

                if (!pointerField.empty())
                {
                    object.pointerField =
                        pointerField;
                }

                objects[event.subject] = object;
                break;
            }

            case TraceEventType::CreateValue:
            {
                StackValueState value;
                value.name = event.subject;
                value.typeName =
                    extractDetailValue(
                        event.detail,
                        "type"
                    );
                value.value =
                    extractDetailValue(
                        event.detail,
                        "value"
                    );

                if (value.typeName.empty())
                {
                    value.typeName = "int";
                }

                if (!activeScopes.empty())
                {
                    value.scopeName =
                        activeScopes.back();
                }

                stackValues[event.subject] =
                    value;

                break;
            }

            case TraceEventType::BindAlias:
            {
                AliasState alias;
                alias.name = event.subject;
                alias.target =
                    extractDetailValue(
                        event.detail,
                        "target"
                    );
                alias.typeName =
                    extractDetailValue(
                        event.detail,
                        "type"
                    );
                alias.isConst =
                    extractDetailValue(
                        event.detail,
                        "const"
                    ) == "true";

                if (!activeScopes.empty())
                {
                    alias.scopeName =
                        activeScopes.back();
                }

                aliases[event.subject] =
                    alias;

                break;
            }

            case TraceEventType::WriteValue:
            {
                auto valueIt =
                    stackValues.find(event.subject);

                if (valueIt != stackValues.end())
                {
                    valueIt->second.value =
                        extractDetailValue(
                            event.detail,
                            "value"
                        );
                }
                else
                {
                    auto resourceIt =
                        resources.find(event.subject);

                    if (resourceIt != resources.end())
                    {
                        resourceIt->second.value =
                            extractDetailValue(
                                event.detail,
                                "value"
                            );
                    }
                }

                break;
            }

            case TraceEventType::AllocateResource:
            {
                HeapResourceState resource;
                resource.id = event.subject;
                resource.value =
                    parseResourceValue(event.detail);
                resource.alive = true;

                resources[event.subject] = resource;
                break;
            }

            case TraceEventType::BindPointer:
            {
                const std::string objectName =
                    objectNameFromPointer(event.subject);

                auto objectIt =
                    objects.find(objectName);

                if (objectIt != objects.end())
                {
                    const std::string fieldName =
                        fieldNameFromPointer(
                            event.subject
                        );

                    if (!fieldName.empty())
                    {
                        objectIt->second.pointerField =
                            fieldName;
                    }

                    objectIt->second.pointsTo =
                        trim(event.detail);
                }

                break;
            }

            case TraceEventType::MoveResource:
            {
                const auto [sourcePointer, destinationPointer] =
                    parseArrow(event.detail);

                const std::string sourceObject =
                    objectNameFromPointer(
                        sourcePointer
                    );

                const std::string destinationObject =
                    objectNameFromPointer(
                        destinationPointer
                    );

                auto destinationIt =
                    objects.find(destinationObject);

                if (destinationIt != objects.end())
                {
                    const std::string fieldName =
                        fieldNameFromPointer(
                            destinationPointer
                        );

                    if (!fieldName.empty())
                    {
                        destinationIt->second.pointerField =
                            fieldName;
                    }

                    destinationIt->second.pointsTo =
                        event.subject;
                }

                const bool exclusiveTransfer =
                    extractDetailValue(
                        event.detail,
                        "transfer"
                    ) == "exclusive";

                if (exclusiveTransfer)
                {
                    auto sourceIt =
                        objects.find(sourceObject);

                    if (sourceIt != objects.end())
                    {
                        const std::string fieldName =
                            fieldNameFromPointer(
                                sourcePointer
                            );

                        if (!fieldName.empty())
                        {
                            sourceIt->second.pointerField =
                                fieldName;
                        }

                        sourceIt->second.pointsTo.clear();
                    }
                }

                break;
            }

            case TraceEventType::SetNull:
            {
                const std::string objectName =
                    objectNameFromPointer(event.subject);

                auto objectIt =
                    objects.find(objectName);

                if (objectIt != objects.end())
                {
                    objectIt->second.pointsTo.clear();
                }

                break;
            }

            case TraceEventType::DestroyBegin:
            {
                auto objectIt =
                    objects.find(event.subject);

                if (objectIt != objects.end())
                {
                    objectIt->second.destroying = true;
                }

                break;
            }

            case TraceEventType::DestroyEnd:
            case TraceEventType::DestroyObject:
            {
                auto objectIt =
                    objects.find(event.subject);

                if (objectIt != objects.end())
                {
                    objectIt->second.alive = false;
                    objectIt->second.destroying = false;
                    objectIt->second.pointsTo.clear();
                }

                break;
            }

            case TraceEventType::FreeResource:
            {
                auto resourceIt =
                    resources.find(event.subject);

                if (resourceIt != resources.end())
                {
                    resourceIt->second.alive = false;
                }

                break;
            }

            case TraceEventType::CopyResource:
            case TraceEventType::Warning:
                // These events currently annotate the timeline but do not
                // directly change the move-exercise memory model.
                break;
        }

        MemorySnapshot snapshot;
        snapshot.step = step++;
        snapshot.cause = event;
        snapshot.activeScopes = activeScopes;
        snapshot.stackObjects =
            copyObjects(objects);
        snapshot.stackValues =
            copyStackValues(stackValues);
        snapshot.aliases =
            copyAliases(aliases);
        snapshot.heapResources =
            copyResources(resources);

        timeline.snapshots.push_back(
            std::move(snapshot)
        );
    }

    return timeline;
}
