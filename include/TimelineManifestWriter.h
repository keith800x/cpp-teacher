#pragma once

#include <filesystem>

class TimelineManifestWriter
{
public:
    void rebuild(
        const std::filesystem::path& outputDirectory,
        const std::filesystem::path& exercisesDirectory,
        const std::filesystem::path& manifestPath
    ) const;
};
