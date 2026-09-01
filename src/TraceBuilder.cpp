#include "TraceBuilder.h"

namespace
{
bool contains(const std::string& source, const std::string& text)
{
    return source.find(text) != std::string::npos;
}
}

SemanticTrace TraceBuilder::build(
    const Exercise& exercise,
    const std::string& studentCode
) const
{
    SemanticTrace trace;

    if (exercise.getId() == "copy_constructor_001")
    {
        trace.events.push_back({
            TraceEventType::CreateObject,
            "original",
            "Original Buffer is created."
        });

        trace.events.push_back({
            TraceEventType::AllocateResource,
            "resource#1",
            "original.data_ owns resource#1."
        });

        trace.events.push_back({
            TraceEventType::CreateObject,
            "copy",
            "Copy construction begins."
        });

        if (contains(studentCode, "new int(*other.data_)"))
        {
            trace.events.push_back({
                TraceEventType::AllocateResource,
                "resource#2",
                "A second heap allocation is created for the copy."
            });

            trace.events.push_back({
                TraceEventType::CopyResource,
                "resource#1 -> resource#2",
                "The value is copied into independent storage."
            });

            trace.events.push_back({
                TraceEventType::DestroyObject,
                "copy",
                "copy is destroyed."
            });

            trace.events.push_back({
                TraceEventType::FreeResource,
                "resource#2",
                "copy releases its own resource."
            });

            trace.events.push_back({
                TraceEventType::DestroyObject,
                "original",
                "original is destroyed."
            });

            trace.events.push_back({
                TraceEventType::FreeResource,
                "resource#1",
                "original releases its own resource."
            });
        }
        else if (contains(studentCode, "data_(other.data_)"))
        {
            trace.events.push_back({
                TraceEventType::CopyResource,
                "resource#1",
                "Only the pointer value is copied. Both objects now refer to resource#1."
            });

            trace.events.push_back({
                TraceEventType::Warning,
                "shared raw pointer",
                "Both Buffer objects believe they own the same allocation."
            });

            trace.events.push_back({
                TraceEventType::DestroyObject,
                "copy",
                "copy destroys resource#1 first."
            });

            trace.events.push_back({
                TraceEventType::FreeResource,
                "resource#1",
                "resource#1 is freed."
            });

            trace.events.push_back({
                TraceEventType::DestroyObject,
                "original",
                "original still contains the old pointer."
            });

            trace.events.push_back({
                TraceEventType::Warning,
                "double-delete",
                "original would attempt to delete an already-freed allocation."
            });
        }

        return trace;
    }

    if (exercise.getId() == "move_constructor_001")
    {
        trace.events.push_back({
            TraceEventType::CreateObject,
            "source",
            "Source Buffer is created."
        });

        trace.events.push_back({
            TraceEventType::AllocateResource,
            "resource#1",
            "source.data_ owns resource#1."
        });

        trace.events.push_back({
            TraceEventType::CreateObject,
            "destination",
            "Move construction begins."
        });

        if (contains(studentCode, "data_(other.data_)"))
        {
            trace.events.push_back({
                TraceEventType::MoveResource,
                "resource#1",
                "destination receives the pointer to resource#1."
            });
        }
        else if (contains(studentCode, "new int(*other.data_)"))
        {
            trace.events.push_back({
                TraceEventType::AllocateResource,
                "resource#2",
                "A new resource is allocated instead of transferring resource#1."
            });

            trace.events.push_back({
                TraceEventType::CopyResource,
                "resource#1 -> resource#2",
                "The value was copied, not moved."
            });
        }

        if (contains(studentCode, "other.data_ = nullptr") ||
            contains(studentCode, "other.data_=nullptr"))
        {
            trace.events.push_back({
                TraceEventType::SetNull,
                "source.data_",
                "source.data_ is cleared, so source no longer owns resource#1."
            });
        }
        else
        {
            trace.events.push_back({
                TraceEventType::Warning,
                "source.data_",
                "The source pointer was not cleared."
            });
        }

        trace.events.push_back({
            TraceEventType::DestroyObject,
            "destination",
            "destination is destroyed."
        });

        trace.events.push_back({
            TraceEventType::FreeResource,
            "resource#1",
            "Transferred resource is released by destination."
        });

        trace.events.push_back({
            TraceEventType::DestroyObject,
            "source",
            "Moved-from source is destroyed."
        });

        return trace;
    }

    return trace;
}


SemanticTrace TraceBuilder::deriveRuntimeTrace(
    const Exercise& exercise,
    const SemanticTrace& runtimeTrace,
    bool submissionPassed
) const
{
    if (exercise.getTraceMode() != "runtime_derived_raii" ||
        !submissionPassed)
    {
        return runtimeTrace;
    }

    SemanticTrace derived;

    derived.events.push_back({
        TraceEventType::EnterScope,
        "processVideoFrame",
        "function scope entered"
    });

    bool frameScopeEntered = false;
    bool frameScopeExited = false;

    for (const TraceEvent& event :
         runtimeTrace.events)
    {
        if (!frameScopeEntered &&
            event.type == TraceEventType::CreateObject &&
            event.subject == "decodeScratch")
        {
            derived.events.push_back({
                TraceEventType::EnterScope,
                "frame-processing",
                "temporary frame-processing scope entered"
            });

            frameScopeEntered = true;
        }

        derived.events.push_back(event);

        if (!frameScopeExited &&
            event.type == TraceEventType::DestroyEnd &&
            event.subject == "decodeScratch")
        {
            derived.events.push_back({
                TraceEventType::ExitScope,
                "frame-processing",
                "scratch-buffer scope exited before upload"
            });

            frameScopeExited = true;
        }
    }

    derived.events.push_back({
        TraceEventType::ExitScope,
        "processVideoFrame",
        "function scope exited"
    });

    return derived;
}
