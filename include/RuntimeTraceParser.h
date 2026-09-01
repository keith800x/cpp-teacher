#pragma once

#include "Trace.h"

#include <string>

class RuntimeTraceParser
{
public:
    SemanticTrace parse(const std::string& stderrText) const;
};
