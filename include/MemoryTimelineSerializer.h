#pragma once

#include "MemoryState.h"

#include <filesystem>
#include <string>

class MemoryTimelineSerializer
{
public:
    std::string toJsonString(
        const MemoryTimeline& timeline,
        const std::string& exerciseId
    ) const;

    void writeJsonFile(
        const MemoryTimeline& timeline,
        const std::string& exerciseId,
        const std::filesystem::path& outputPath
    ) const;
};
