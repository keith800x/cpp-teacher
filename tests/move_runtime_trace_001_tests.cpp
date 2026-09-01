#include <cstdio>
#include <utility>

int main()
{
    int failureCode = 0;

    std::fprintf(
        stderr,
        "TRACE|ENTER_SCOPE|retry-dispatch|failed upload retry\n"
    );

    std::fprintf(
        stderr,
        "TRACE|CREATE_OBJECT|failedPacket|type=UploadPacket|pointer=payload_\n"
    );

    {
        UploadPacket failedPacket(4096);

        if (failedPacket.empty() ||
            failedPacket.payload() == nullptr)
        {
            return 2;
        }

        const int originalResourceId =
            failedPacket.payload()->id();

        std::fprintf(
            stderr,
            "TRACE|BIND_POINTER|failedPacket.payload_|resource#%d\n",
            originalResourceId
        );

        std::fprintf(
            stderr,
            "TRACE|CREATE_OBJECT|retryPacket|type=UploadPacket|pointer=payload_\n"
        );

        {
            UploadPacket retryPacket(
                std::move(failedPacket)
            );

            const bool destinationHasOriginal =
                retryPacket.payload() != nullptr &&
                retryPacket.payload()->id() ==
                    originalResourceId;

            const bool sourceIsEmpty =
                failedPacket.empty() &&
                failedPacket.payload() == nullptr;

            if (destinationHasOriginal)
            {
                std::fprintf(
                    stderr,
                    "TRACE|MOVE_RESOURCE|resource#%d|failedPacket.payload_ -> retryPacket.payload_|transfer=exclusive\n",
                    originalResourceId
                );
            }
            else
            {
                std::fprintf(
                    stderr,
                    "TRACE|WARNING|ownership|retry packet owns a different payload allocation\n"
                );

                failureCode = 3;
            }

            if (!sourceIsEmpty)
            {
                std::fprintf(
                    stderr,
                    "TRACE|WARNING|failedPacket.payload_|moved-from packet still owns its payload\n"
                );

                if (failureCode == 0)
                {
                    failureCode = 4;
                }
            }

            if (retryPacket.empty())
            {
                if (failureCode == 0)
                {
                    failureCode = 5;
                }
            }
            else if (retryPacket.bytes() != 4096)
            {
                if (failureCode == 0)
                {
                    failureCode = 6;
                }
            }

            std::fprintf(
                stderr,
                "TRACE|DESTROY_BEGIN|retryPacket|retry packet leaves scope\n"
            );
        }

        std::fprintf(
            stderr,
            "TRACE|DESTROY_END|retryPacket|retry packet destroyed\n"
        );

        std::fprintf(
            stderr,
            "TRACE|DESTROY_BEGIN|failedPacket|moved-from packet leaves scope\n"
        );
    }

    std::fprintf(
        stderr,
        "TRACE|DESTROY_END|failedPacket|moved-from packet destroyed\n"
    );

    std::fprintf(
        stderr,
        "TRACE|EXIT_SCOPE|retry-dispatch|retry dispatch completed\n"
    );

    if (failureCode != 0)
    {
        std::fprintf(
            stderr,
            "Move construction must transfer the original payload without "
            "allocating a replacement and must leave the source empty.\n"
        );
    }

    return failureCode;
}
