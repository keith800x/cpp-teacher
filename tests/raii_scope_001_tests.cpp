#include <cstdio>
#include <string>
#include <vector>

int main()
{
    resetFrameBufferAudit();

    processVideoFrame();

    const std::vector<std::string> expected = {
        "construct:outputBuffer",
        "construct:decodeScratch",
        "construct:filterScratch",
        "decode:decodeScratch",
        "filter:filterScratch",
        "destroy:filterScratch",
        "destroy:decodeScratch",
        "upload:outputBuffer",
        "destroy:outputBuffer"
    };

    if (!frameBufferAuditMatches(expected))
    {
        std::fprintf(
            stderr,
            "The scratch buffers must be destroyed before uploadFrame runs. "
            "Keep decodeScratch before filterScratch and preserve decode/filter calls.\n"
        );

        std::fprintf(
            stderr,
            "Observed lifecycle:\n"
        );

        for (const std::string& event :
             frameBufferAudit())
        {
            std::fprintf(
                stderr,
                "  %s\n",
                event.c_str()
            );
        }

        return 2;
    }

    return 0;
}
