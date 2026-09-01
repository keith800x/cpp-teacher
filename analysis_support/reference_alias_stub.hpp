class ScopeMarker
{
public:
    explicit ScopeMarker(const char*);
};

void traceValueCreated(const char*, int);

void traceAliasBound(
    const char*,
    const int&,
    const char*,
    const int&,
    bool
);

void traceValueWrite(
    const char*,
    const char*,
    int
);
