#include <cstdio>
#include <string>

class ScopeMarker
{
public:
    explicit ScopeMarker(const char* name)
        : name_(name)
    {
        std::fprintf(
            stderr,
            "TRACE|ENTER_SCOPE|%s|scope entered\n",
            name_.c_str()
        );
    }

    ~ScopeMarker()
    {
        std::fprintf(
            stderr,
            "TRACE|EXIT_SCOPE|%s|scope exited\n",
            name_.c_str()
        );
    }

private:
    std::string name_;
};

inline void traceValueCreated(
    const char* name,
    int value
)
{
    std::fprintf(
        stderr,
        "TRACE|CREATE_VALUE|%s|type=int|value=%d\n",
        name,
        value
    );
}

inline void traceAliasBound(
    const char* aliasName,
    const int& aliasValue,
    const char* targetName,
    const int& targetValue,
    bool isConst
)
{
    if (&aliasValue != &targetValue)
    {
        std::fprintf(
            stderr,
            "TRACE|WARNING|%s|alias does not reference requested target\n",
            aliasName
        );

        return;
    }

    std::fprintf(
        stderr,
        "TRACE|BIND_ALIAS|%s|target=%s|type=%s|const=%s\n",
        aliasName,
        targetName,
        isConst ? "const int&" : "int&",
        isConst ? "true" : "false"
    );
}

inline void traceValueWrite(
    const char* valueName,
    const char* viaAlias,
    int value
)
{
    std::fprintf(
        stderr,
        "TRACE|WRITE_VALUE|%s|via=%s|value=%d\n",
        valueName,
        viaAlias,
        value
    );
}
