#include <cstdio>
#include <string>
#include <utility>
#include <vector>

inline std::vector<std::string>&
raiiScopeStack()
{
    static std::vector<std::string> values;
    return values;
}

inline std::vector<std::string>&
raiiConstructionAudit()
{
    static std::vector<std::string> values;
    return values;
}

inline std::vector<std::string>&
raiiDestructionAudit()
{
    static std::vector<std::string> values;
    return values;
}

inline std::vector<std::pair<std::string, std::string>>&
raiiScopeAudit()
{
    static std::vector<
        std::pair<std::string, std::string>
    > values;

    return values;
}

inline void resetRaiiAudit()
{
    raiiScopeStack().clear();
    raiiConstructionAudit().clear();
    raiiDestructionAudit().clear();
    raiiScopeAudit().clear();
}

inline std::string currentRaiiScope()
{
    if (raiiScopeStack().empty())
    {
        return {};
    }

    return raiiScopeStack().back();
}

inline bool raiiConstructionOrderCorrect()
{
    const std::vector<std::string> expected = {
        "outputBuffer",
        "decodeScratch",
        "filterScratch"
    };

    return raiiConstructionAudit() == expected;
}

inline bool raiiDestructionOrderCorrect()
{
    const std::vector<std::string> expected = {
        "filterScratch",
        "decodeScratch",
        "outputBuffer"
    };

    return raiiDestructionAudit() == expected;
}

inline bool raiiScopePlacementCorrect()
{
    const std::vector<
        std::pair<std::string, std::string>
    > expected = {
        {"outputBuffer", "video-job"},
        {"decodeScratch", "frame"},
        {"filterScratch", "frame"}
    };

    return raiiScopeAudit() == expected;
}

class ScopeMarker
{
public:
    explicit ScopeMarker(const char* name)
        : name_(name)
    {
        raiiScopeStack().push_back(
            name_
        );

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

        if (!raiiScopeStack().empty())
        {
            raiiScopeStack().pop_back();
        }
    }

private:
    std::string name_;
};

class RaiiTrackedResource
{
public:
    explicit RaiiTrackedResource(int value)
        : id_(nextId_++),
          value_(value)
    {
        std::fprintf(
            stderr,
            "TRACE|ALLOCATE_RESOURCE|resource#%d|value=%d\n",
            id_,
            value_
        );
    }

    ~RaiiTrackedResource()
    {
        std::fprintf(
            stderr,
            "TRACE|FREE_RESOURCE|resource#%d|RAII resource destructor\n",
            id_
        );
    }

    int id() const
    {
        return id_;
    }

    int value() const
    {
        return value_;
    }

private:
    inline static int nextId_ = 1;

    int id_;
    int value_;
};

class RaiiBuffer
{
public:
    RaiiBuffer(
        const char* objectName,
        int value
    )
        : objectName_(objectName),
          data_(nullptr)
    {
        raiiConstructionAudit().push_back(
            objectName_
        );

        raiiScopeAudit().push_back({
            objectName_,
            currentRaiiScope()
        });

        std::fprintf(
            stderr,
            "TRACE|CREATE_OBJECT|%s|type=RaiiBuffer\n",
            objectName_.c_str()
        );

        data_ =
            new RaiiTrackedResource(value);

        std::fprintf(
            stderr,
            "TRACE|BIND_POINTER|%s.data_|resource#%d\n",
            objectName_.c_str(),
            data_->id()
        );
    }

    RaiiBuffer(const RaiiBuffer&) = delete;
    RaiiBuffer& operator=(const RaiiBuffer&) = delete;

    ~RaiiBuffer()
    {
        raiiDestructionAudit().push_back(
            objectName_
        );

        std::fprintf(
            stderr,
            "TRACE|DESTROY_BEGIN|%s|RAII destructor begins\n",
            objectName_.c_str()
        );

        delete data_;
        data_ = nullptr;

        std::fprintf(
            stderr,
            "TRACE|DESTROY_END|%s|RAII destructor completed\n",
            objectName_.c_str()
        );
    }

private:
    std::string objectName_;
    RaiiTrackedResource* data_;
};
