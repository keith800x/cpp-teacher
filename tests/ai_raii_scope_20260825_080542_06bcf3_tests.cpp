#include <cstdio>
#include <string>
#include <vector>

int main()
{
    resetHarborAudit();

    std::fprintf(stderr, "TRACE|ENTER_SCOPE|publishMorningBulletin|morning harbor bulletin workflow\n");
    publishMorningBulletin();
    std::fprintf(stderr, "TRACE|EXIT_SCOPE|publishMorningBulletin|morning harbor bulletin workflow complete\n");

    const std::vector<std::string> expected = {
        "create:morningBulletin",
        "open:gaugeSession",
        "capture:gaugeSession->morningBulletin",
        "close:gaugeSession",
        "transmit:morningBulletin",
        "destroy:morningBulletin"
    };

    if (!harborAuditMatches(expected))
    {
        std::fprintf(stderr, "The tide gauge session must close after readings are captured and before radio transmission begins.\n");
        std::fprintf(stderr, "Observed lifecycle:\n");
        for (const std::string& event : harborAudit())
        {
            std::fprintf(stderr, "  %s\n", event.c_str());
        }
        return 2;
    }

    return 0;
}
