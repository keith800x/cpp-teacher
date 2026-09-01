#include "MemoryStatePrinter.h"

#include "Trace.h"

#include <iostream>

namespace
{
void printStackObject(
    const StackObjectState& object
)
{
    std::cout
        << "  "
        << object.name
        << " : "
        << object.typeName;

    if (!object.scopeName.empty())
    {
        std::cout << " @ scope=" << object.scopeName;
    }

    if (!object.alive)
    {
        std::cout << " [destroyed]";
    }
    else if (object.destroying)
    {
        std::cout << " [destroying]";
    }

    std::cout << '\n';

    if (object.alive)
    {
        std::cout
            << "    "
            << object.pointerField
            << " -> ";

        if (object.pointsTo.empty())
        {
            std::cout << "nullptr";
        }
        else
        {
            std::cout << object.pointsTo;
        }

        std::cout << '\n';
    }
}

void printHeapResource(
    const HeapResourceState& resource
)
{
    std::cout
        << "  "
        << resource.id;

    if (!resource.alive)
    {
        std::cout << " [freed]";
    }

    if (!resource.value.empty())
    {
        std::cout
            << " { value="
            << resource.value
            << " }";
    }

    std::cout << '\n';
}
}

void MemoryStatePrinter::print(
    const MemoryTimeline& timeline
) const
{
    if (timeline.snapshots.empty())
    {
        return;
    }

    std::cout << "\n========================================\n";
    std::cout << "          MEMORY SNAPSHOTS\n";
    std::cout << "========================================\n";

    for (const MemorySnapshot& snapshot :
         timeline.snapshots)
    {
        std::cout
            << "\n--- STEP "
            << snapshot.step
            << " after "
            << toString(snapshot.cause.type)
            << " ---\n";

        std::cout
            << "Event: "
            << snapshot.cause.subject
            << " | "
            << snapshot.cause.detail
            << "\n\n";

        std::cout << "ACTIVE SCOPES\n";

        if (snapshot.activeScopes.empty())
        {
            std::cout << "  (none)\n";
        }
        else
        {
            for (std::size_t i = 0; i < snapshot.activeScopes.size(); ++i)
            {
                std::cout << "  " << i << ": " << snapshot.activeScopes[i] << '\n';
            }
        }

        std::cout << "\nSTACK VALUES\n";

        if (snapshot.stackValues.empty())
        {
            std::cout << "  (none)\n";
        }
        else
        {
            for (const StackValueState& value :
                 snapshot.stackValues)
            {
                std::cout
                    << "  "
                    << value.name
                    << " : "
                    << value.typeName
                    << " = "
                    << value.value;

                if (!value.alive)
                {
                    std::cout << " [out of scope]";
                }

                std::cout << '\n';
            }
        }

        std::cout << "\nALIASES\n";

        if (snapshot.aliases.empty())
        {
            std::cout << "  (none)\n";
        }
        else
        {
            for (const AliasState& alias :
                 snapshot.aliases)
            {
                std::cout
                    << "  "
                    << alias.name
                    << " : "
                    << alias.typeName
                    << " -> "
                    << alias.target;

                if (alias.isConst)
                {
                    std::cout << " [const]";
                }

                if (!alias.alive)
                {
                    std::cout << " [out of scope]";
                }

                std::cout << '\n';
            }
        }

        std::cout << "\nSTACK OBJECTS\n";

        if (snapshot.stackObjects.empty())
        {
            std::cout << "  (empty)\n";
        }
        else
        {
            for (const StackObjectState& object :
                 snapshot.stackObjects)
            {
                printStackObject(object);
            }
        }

        std::cout << "HEAP\n";

        if (snapshot.heapResources.empty())
        {
            std::cout << "  (empty)\n";
        }
        else
        {
            for (const HeapResourceState& resource :
                 snapshot.heapResources)
            {
                printHeapResource(resource);
            }
        }
    }
}
