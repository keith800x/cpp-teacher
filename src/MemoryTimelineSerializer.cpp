#include "MemoryTimelineSerializer.h"

#include "Trace.h"

#include <filesystem>
#include <fstream>
#include <stdexcept>

#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace
{
json stackObjectToJson(
    const StackObjectState& object
)
{
    std::string lifetime = "alive";

    if (!object.alive)
    {
        lifetime = "destroyed";
    }
    else if (object.destroying)
    {
        lifetime = "destroying";
    }

    json result = {
        {"name", object.name},
        {"type", object.typeName},
        {"scope", object.scopeName.empty() ? json(nullptr) : json(object.scopeName)},
        {"alive", object.alive},
        {"lifetime", lifetime},
        {"fields", json::object()}
    };

    if (object.alive)
    {
        result["fields"][object.pointerField] = {
            {"kind", "pointer"},
            {"points_to",
                object.pointsTo.empty()
                    ? json(nullptr)
                    : json(object.pointsTo)}
        };
    }

    return result;
}


json stackValueToJson(
    const StackValueState& value
)
{
    return {
        {"name", value.name},
        {"type", value.typeName},
        {"scope",
            value.scopeName.empty()
                ? json(nullptr)
                : json(value.scopeName)},
        {"value", value.value},
        {"alive", value.alive}
    };
}

json aliasToJson(
    const AliasState& alias
)
{
    return {
        {"name", alias.name},
        {"type", alias.typeName},
        {"scope",
            alias.scopeName.empty()
                ? json(nullptr)
                : json(alias.scopeName)},
        {"target", alias.target},
        {"const", alias.isConst},
        {"alive", alias.alive}
    };
}

json heapResourceToJson(
    const HeapResourceState& resource
)
{
    json result = {
        {"id", resource.id},
        {"alive", resource.alive}
    };

    if (!resource.value.empty())
    {
        result["value"] = resource.value;
    }
    else
    {
        result["value"] = nullptr;
    }

    return result;
}

json traceEventToJson(
    const TraceEvent& event
)
{
    return {
        {"type", toString(event.type)},
        {"subject", event.subject},
        {"detail", event.detail}
    };
}
}

std::string MemoryTimelineSerializer::toJsonString(
    const MemoryTimeline& timeline,
    const std::string& exerciseId
) const
{
    json document = {
        {"schema_version", 4},
        {"exercise_id", exerciseId},
        {"timeline", json::array()}
    };

    for (const MemorySnapshot& snapshot :
         timeline.snapshots)
    {
        json snapshotJson = {
            {"step", snapshot.step},
            {"cause", traceEventToJson(snapshot.cause)},
            {"active_scopes", snapshot.activeScopes},
            {"stack", json::array()},
            {"stack_values", json::array()},
            {"aliases", json::array()},
            {"heap", json::array()}
        };

        for (const StackObjectState& object :
             snapshot.stackObjects)
        {
            snapshotJson["stack"].push_back(
                stackObjectToJson(object)
            );
        }

        for (const StackValueState& value :
             snapshot.stackValues)
        {
            snapshotJson["stack_values"].push_back(
                stackValueToJson(value)
            );
        }

        for (const AliasState& alias :
             snapshot.aliases)
        {
            snapshotJson["aliases"].push_back(
                aliasToJson(alias)
            );
        }

        for (const HeapResourceState& resource :
             snapshot.heapResources)
        {
            snapshotJson["heap"].push_back(
                heapResourceToJson(resource)
            );
        }

        document["timeline"].push_back(
            std::move(snapshotJson)
        );
    }

    return document.dump(2);
}

void MemoryTimelineSerializer::writeJsonFile(
    const MemoryTimeline& timeline,
    const std::string& exerciseId,
    const std::filesystem::path& outputPath
) const
{
    const std::filesystem::path parent =
        outputPath.parent_path();

    if (!parent.empty())
    {
        std::filesystem::create_directories(parent);
    }

    std::ofstream file(outputPath);

    if (!file)
    {
        throw std::runtime_error(
            "Could not create timeline JSON file: " +
            outputPath.string()
        );
    }

    file
        << toJsonString(timeline, exerciseId)
        << '\n';
}
