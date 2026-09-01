#include "TimelineManifestWriter.h"

#include <algorithm>
#include <fstream>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace
{
struct ExerciseMetadata
{
    std::string title;
    std::string topic;
};

json readJsonFile(
    const std::filesystem::path& path
)
{
    std::ifstream file(path);

    if (!file)
    {
        throw std::runtime_error(
            "Could not open JSON file: " +
            path.string()
        );
    }

    json document;
    file >> document;
    return document;
}

bool endsWith(
    const std::string& value,
    const std::string& suffix
)
{
    if (value.size() < suffix.size())
    {
        return false;
    }

    return value.compare(
        value.size() - suffix.size(),
        suffix.size(),
        suffix
    ) == 0;
}

std::map<std::string, ExerciseMetadata>
loadExerciseMetadata(
    const std::filesystem::path& exercisesDirectory
)
{
    std::map<std::string, ExerciseMetadata> metadata;

    if (!std::filesystem::exists(exercisesDirectory))
    {
        return metadata;
    }

    for (const auto& entry :
         std::filesystem::directory_iterator(
             exercisesDirectory
         ))
    {
        if (!entry.is_regular_file() ||
            entry.path().extension() != ".json")
        {
            continue;
        }

        try
        {
            const json document =
                readJsonFile(entry.path());

            const std::string id =
                document.value("id", "");

            if (id.empty())
            {
                continue;
            }

            ExerciseMetadata item;
            item.title =
                document.value("title", id);
            item.topic =
                document.value("topic", "");

            metadata[id] =
                std::move(item);
        }
        catch (...)
        {
            // A malformed unrelated exercise file should not stop
            // the visualizer manifest from being rebuilt.
        }
    }

    return metadata;
}
}

void TimelineManifestWriter::rebuild(
    const std::filesystem::path& outputDirectory,
    const std::filesystem::path& exercisesDirectory,
    const std::filesystem::path& manifestPath
) const
{
    std::filesystem::create_directories(
        outputDirectory
    );

    const auto exerciseMetadata =
        loadExerciseMetadata(
            exercisesDirectory
        );

    std::vector<json> lessons;

    for (const auto& entry :
         std::filesystem::directory_iterator(
             outputDirectory
         ))
    {
        if (!entry.is_regular_file())
        {
            continue;
        }

        const std::string filename =
            entry.path().filename().string();

        if (!endsWith(
                filename,
                "_memory_timeline.json"
            ))
        {
            continue;
        }

        try
        {
            const json timeline =
                readJsonFile(entry.path());

            const std::string exerciseId =
                timeline.value(
                    "exercise_id",
                    ""
                );

            if (exerciseId.empty())
            {
                continue;
            }

            const int schemaVersion =
                timeline.value(
                    "schema_version",
                    0
                );

            std::string title = exerciseId;
            std::string topic;

            const auto metadataIt =
                exerciseMetadata.find(
                    exerciseId
                );

            if (metadataIt !=
                exerciseMetadata.end())
            {
                title =
                    metadataIt->second.title;
                topic =
                    metadataIt->second.topic;
            }

            lessons.push_back({
                {"exercise_id", exerciseId},
                {"title", title},
                {"topic", topic},
                {"schema_version", schemaVersion},
                {"timeline_file", filename}
            });
        }
        catch (...)
        {
            // Ignore malformed or partially-written timeline files.
        }
    }

    std::sort(
        lessons.begin(),
        lessons.end(),
        [](
            const json& left,
            const json& right
        )
        {
            return left.value(
                       "title",
                       ""
                   ) <
                   right.value(
                       "title",
                       ""
                   );
        }
    );

    json manifest = {
        {"manifest_version", 1},
        {"lessons", lessons}
    };

    const std::filesystem::path parent =
        manifestPath.parent_path();

    if (!parent.empty())
    {
        std::filesystem::create_directories(
            parent
        );
    }

    std::ofstream file(manifestPath);

    if (!file)
    {
        throw std::runtime_error(
            "Could not create timeline manifest: " +
            manifestPath.string()
        );
    }

    file << manifest.dump(2) << '\n';
}
