#include <cstdio>
#include <string>
#include <vector>

namespace {
std::size_t eventIndex(const std::vector<std::string>& events, const std::string& wanted)
{
    for (std::size_t i = 0; i < events.size(); ++i)
        if (events[i] == wanted) return i;
    return events.size();
}

bool exactlyOnce(const std::vector<std::string>& events, const std::string& wanted)
{
    std::size_t count = 0;
    for (const std::string& event : events)
        if (event == wanted) ++count;
    return count == 1;
}

bool before(const std::vector<std::string>& events,
            const std::string& first,
            const std::string& second)
{
    const auto a = eventIndex(events, first);
    const auto b = eventIndex(events, second);
    return a < events.size() && b < events.size() && a < b;
}

bool requireEvent(const std::vector<std::string>& events, const std::string& event)
{
    if (exactlyOnce(events, event)) return true;
    std::fprintf(stderr, "Expected exactly one lifecycle event: %s\n", event.c_str());
    return false;
}

bool requireBefore(const std::vector<std::string>& events,
                   const std::string& first,
                   const std::string& second)
{
    if (before(events, first, second)) return true;
    std::fprintf(stderr, "Expected lifecycle ordering: %s before %s\n",
                 first.c_str(), second.c_str());
    return false;
}
}

int main()
{
    resetMuseumAudit();
    std::fprintf(stderr, "TRACE|ENTER_SCOPE|prepareEveningExhibit|preparing the evening gallery\n");
    MuseumClimateController controller;
    controller.prepareEveningExhibit();
    std::fprintf(stderr, "TRACE|EXIT_SCOPE|prepareEveningExhibit|evening gallery preparation complete\n");

    const auto& events = museumAudit();
    bool ok = true;

    const std::vector<std::string> required = {
        "create:eveningBrief",
        "open:securityOverride",
        "open:calibrationConsole",
        "calibrate:calibrationConsole->eveningBrief",
        "close:calibrationConsole",
        "review:securityOverride->eveningBrief",
        "close:securityOverride",
        "open:projectionRig",
        "render:projectionRig->eveningBrief",
        "close:projectionRig",
        "announce:eveningBrief",
        "destroy:eveningBrief"
    };

    for (const auto& event : required)
        ok = requireEvent(events, event) && ok;

    // Persistent brief.
    ok = requireBefore(events, "create:eveningBrief", "calibrate:calibrationConsole->eveningBrief") && ok;
    ok = requireBefore(events, "announce:eveningBrief", "destroy:eveningBrief") && ok;

    // Calibration lifetime.
    ok = requireBefore(events, "open:calibrationConsole", "calibrate:calibrationConsole->eveningBrief") && ok;
    ok = requireBefore(events, "calibrate:calibrationConsole->eveningBrief", "close:calibrationConsole") && ok;
    ok = requireBefore(events, "close:calibrationConsole", "review:securityOverride->eveningBrief") && ok;

    // Security lifetime. It may be acquired before or after calibration.
    ok = requireBefore(events, "open:securityOverride", "review:securityOverride->eveningBrief") && ok;
    ok = requireBefore(events, "review:securityOverride->eveningBrief", "close:securityOverride") && ok;
    ok = requireBefore(events, "close:securityOverride", "render:projectionRig->eveningBrief") && ok;

    // Projection lifetime.
    ok = requireBefore(events, "open:projectionRig", "render:projectionRig->eveningBrief") && ok;
    ok = requireBefore(events, "render:projectionRig->eveningBrief", "close:projectionRig") && ok;
    ok = requireBefore(events, "close:projectionRig", "announce:eveningBrief") && ok;

    // Public operation order.
    ok = requireBefore(events, "calibrate:calibrationConsole->eveningBrief", "review:securityOverride->eveningBrief") && ok;
    ok = requireBefore(events, "review:securityOverride->eveningBrief", "render:projectionRig->eveningBrief") && ok;
    ok = requireBefore(events, "render:projectionRig->eveningBrief", "announce:eveningBrief") && ok;

    if (!ok) {
        std::fprintf(stderr, "Observed lifecycle:\n");
        for (const auto& event : events) std::fprintf(stderr, "  %s\n", event.c_str());
        return 2;
    }

    return 0;
}
