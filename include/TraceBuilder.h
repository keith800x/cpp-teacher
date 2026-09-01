#pragma once

#include "Exercise.h"
#include "Trace.h"

#include <string>

class TraceBuilder
{
public:
    SemanticTrace build(
        const Exercise& exercise,
        const std::string& studentCode
    ) const;

    SemanticTrace deriveRuntimeTrace(
        const Exercise& exercise,
        const SemanticTrace& runtimeTrace,
        bool submissionPassed
    ) const;
};
