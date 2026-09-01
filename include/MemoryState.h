#pragma once

#include "Trace.h"

#include <string>
#include <vector>

struct StackObjectState
{
    std::string name;
    std::string typeName = "Buffer";
    std::string scopeName;
    bool alive = true;
    bool destroying = false;

    std::string pointerField = "data_";
    std::string pointsTo;
};


struct StackValueState
{
    std::string name;
    std::string typeName = "int";
    std::string value;
    bool alive = true;
    std::string scopeName;
};

struct AliasState
{
    std::string name;
    std::string typeName;
    std::string target;
    bool isConst = false;
    bool alive = true;
    std::string scopeName;
};

struct HeapResourceState
{
    std::string id;
    std::string value;
    bool alive = true;
};

struct MemorySnapshot
{
    int step = 0;
    TraceEvent cause;

    std::vector<std::string> activeScopes;
    std::vector<StackObjectState> stackObjects;
    std::vector<StackValueState> stackValues;
    std::vector<AliasState> aliases;
    std::vector<HeapResourceState> heapResources;
};

struct MemoryTimeline
{
    std::vector<MemorySnapshot> snapshots;
};
