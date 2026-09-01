#include <cstdio>
#include <type_traits>

int main()
{
    constexpr bool usesWritableReference =
        std::is_same_v<
            decltype(&applyCoolingAdjustment),
            void (*)(int&, int)
        >;

    std::fprintf(
        stderr,
        "TRACE|ENTER_SCOPE|caller|greenhouse cooling cycle\n"
    );

    int greenhouseTarget = 26;

    std::fprintf(
        stderr,
        "TRACE|CREATE_VALUE|greenhouseTarget|type=int|value=%d\n",
        greenhouseTarget
    );

    std::fprintf(
        stderr,
        "TRACE|ENTER_SCOPE|applyCoolingAdjustment|function call\n"
    );

    if constexpr (usesWritableReference)
    {
        std::fprintf(
            stderr,
            "TRACE|BIND_ALIAS|targetTemperature|target=greenhouseTarget|type=int&|const=false\n"
        );
    }
    else
    {
        std::fprintf(
            stderr,
            "TRACE|CREATE_VALUE|targetTemperature|type=int|value=%d\n",
            greenhouseTarget
        );
    }

    applyCoolingAdjustment(greenhouseTarget, 4);

    if constexpr (usesWritableReference)
    {
        std::fprintf(
            stderr,
            "TRACE|WRITE_VALUE|greenhouseTarget|via=targetTemperature|value=%d\n",
            greenhouseTarget
        );
    }
    else
    {
        std::fprintf(
            stderr,
            "TRACE|WRITE_VALUE|targetTemperature|via=applyCoolingAdjustment|value=22\n"
        );
        std::fprintf(
            stderr,
            "TRACE|WARNING|targetTemperature|parameter is a copy; the greenhouse target was not changed\n"
        );
    }

    std::fprintf(
        stderr,
        "TRACE|EXIT_SCOPE|applyCoolingAdjustment|function returned\n"
    );

    std::fprintf(
        stderr,
        "TRACE|EXIT_SCOPE|caller|greenhouse cooling cycle completed\n"
    );

    if (greenhouseTarget != 22)
    {
        std::fprintf(
            stderr,
            "applyCoolingAdjustment must update the caller's temperature target. Expected 22, got %d.\n",
            greenhouseTarget
        );
        return 2;
    }

    if (!usesWritableReference)
    {
        std::fprintf(
            stderr,
            "applyCoolingAdjustment must accept targetTemperature as a writable reference.\n"
        );
        return 3;
    }

    return 0;
}
