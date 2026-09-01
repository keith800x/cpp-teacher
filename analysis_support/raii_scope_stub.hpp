class ScopeMarker
{
public:
    explicit ScopeMarker(const char*);
};

class RaiiBuffer
{
public:
    RaiiBuffer(const char*, int);
    RaiiBuffer(const RaiiBuffer&) = delete;
    RaiiBuffer& operator=(const RaiiBuffer&) = delete;
    ~RaiiBuffer();
};
