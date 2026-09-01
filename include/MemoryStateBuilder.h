#pragma once

#include "MemoryState.h"
#include "Trace.h"

class MemoryStateBuilder
{
public:
    MemoryTimeline build(const SemanticTrace& trace) const;
};
