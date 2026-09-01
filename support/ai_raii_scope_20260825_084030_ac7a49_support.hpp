#include <cstdio>
#include <string>
#include <vector>

inline std::vector<std::string>& museumAudit()
{
    static std::vector<std::string> events;
    return events;
}

inline void resetMuseumAudit()
{
    museumAudit().clear();
}

class ExhibitBrief
{
public:
    explicit ExhibitBrief(const char* label)
        : label_(label)
    {
        museumAudit().push_back("create:" + label_);
        std::fprintf(stderr, "TRACE|CREATE_OBJECT|%s|type=ExhibitBrief\n", label_.c_str());
    }

    ~ExhibitBrief()
    {
        museumAudit().push_back("destroy:" + label_);
        std::fprintf(stderr, "TRACE|DESTROY_BEGIN|%s|ExhibitBrief cleanup begins\n", label_.c_str());
        std::fprintf(stderr, "TRACE|DESTROY_END|%s|ExhibitBrief cleanup completed\n", label_.c_str());
    }

    const std::string& label() const
    {
        return label_;
    }

private:
    std::string label_;
};

class SecurityOverride
{
public:
    explicit SecurityOverride(const char* label)
        : label_(label), resourceId_(nextResourceId_++)
    {
        museumAudit().push_back("open:" + label_);
        std::fprintf(stderr, "TRACE|CREATE_OBJECT|%s|type=SecurityOverride\n", label_.c_str());
        std::fprintf(stderr, "TRACE|ALLOCATE_RESOURCE|resource#%d|value=gallery security override\n", resourceId_);
        std::fprintf(stderr, "TRACE|BIND_POINTER|%s.override_|resource#%d\n", label_.c_str(), resourceId_);
    }

    SecurityOverride(const SecurityOverride&) = delete;
    SecurityOverride& operator=(const SecurityOverride&) = delete;

    ~SecurityOverride()
    {
        museumAudit().push_back("close:" + label_);
        std::fprintf(stderr, "TRACE|DESTROY_BEGIN|%s|SecurityOverride cleanup begins\n", label_.c_str());
        std::fprintf(stderr, "TRACE|FREE_RESOURCE|resource#%d|gallery security override released\n", resourceId_);
        std::fprintf(stderr, "TRACE|DESTROY_END|%s|SecurityOverride cleanup completed\n", label_.c_str());
    }

    const std::string& label() const
    {
        return label_;
    }

private:
    inline static int nextResourceId_ = 1;
    std::string label_;
    int resourceId_;
};

class CalibrationConsole
{
public:
    explicit CalibrationConsole(const char* label)
        : label_(label), resourceId_(nextResourceId_++)
    {
        museumAudit().push_back("open:" + label_);
        std::fprintf(stderr, "TRACE|CREATE_OBJECT|%s|type=CalibrationConsole\n", label_.c_str());
        std::fprintf(stderr, "TRACE|ALLOCATE_RESOURCE|resource#%d|value=display calibration channel\n", resourceId_);
        std::fprintf(stderr, "TRACE|BIND_POINTER|%s.console_|resource#%d\n", label_.c_str(), resourceId_);
    }

    CalibrationConsole(const CalibrationConsole&) = delete;
    CalibrationConsole& operator=(const CalibrationConsole&) = delete;

    ~CalibrationConsole()
    {
        museumAudit().push_back("close:" + label_);
        std::fprintf(stderr, "TRACE|DESTROY_BEGIN|%s|CalibrationConsole cleanup begins\n", label_.c_str());
        std::fprintf(stderr, "TRACE|FREE_RESOURCE|resource#%d|display calibration channel closed\n", resourceId_);
        std::fprintf(stderr, "TRACE|DESTROY_END|%s|CalibrationConsole cleanup completed\n", label_.c_str());
    }

    const std::string& label() const
    {
        return label_;
    }

private:
    inline static int nextResourceId_ = 100;
    std::string label_;
    int resourceId_;
};

class ProjectionRig
{
public:
    explicit ProjectionRig(const char* label)
        : label_(label), resourceId_(nextResourceId_++)
    {
        museumAudit().push_back("open:" + label_);
        std::fprintf(stderr, "TRACE|CREATE_OBJECT|%s|type=ProjectionRig\n", label_.c_str());
        std::fprintf(stderr, "TRACE|ALLOCATE_RESOURCE|resource#%d|value=projection preview channel\n", resourceId_);
        std::fprintf(stderr, "TRACE|BIND_POINTER|%s.rig_|resource#%d\n", label_.c_str(), resourceId_);
    }

    ProjectionRig(const ProjectionRig&) = delete;
    ProjectionRig& operator=(const ProjectionRig&) = delete;

    ~ProjectionRig()
    {
        museumAudit().push_back("close:" + label_);
        std::fprintf(stderr, "TRACE|DESTROY_BEGIN|%s|ProjectionRig cleanup begins\n", label_.c_str());
        std::fprintf(stderr, "TRACE|FREE_RESOURCE|resource#%d|projection preview channel closed\n", resourceId_);
        std::fprintf(stderr, "TRACE|DESTROY_END|%s|ProjectionRig cleanup completed\n", label_.c_str());
    }

    const std::string& label() const
    {
        return label_;
    }

private:
    inline static int nextResourceId_ = 200;
    std::string label_;
    int resourceId_;
};

inline void calibrateDisplay(CalibrationConsole& console, ExhibitBrief& brief)
{
    std::fprintf(stderr, "TRACE|ENTER_SCOPE|calibrateDisplay|calibrating interactive displays\n");
    museumAudit().push_back("calibrate:" + console.label() + "->" + brief.label());
    std::fprintf(stderr, "TRACE|EXIT_SCOPE|calibrateDisplay|display calibration complete\n");
}

inline void reviewEvacuationLights(SecurityOverride& overrideSystem, ExhibitBrief& brief)
{
    std::fprintf(stderr, "TRACE|ENTER_SCOPE|reviewEvacuationLights|reviewing evacuation lighting\n");
    museumAudit().push_back("review:" + overrideSystem.label() + "->" + brief.label());
    std::fprintf(stderr, "TRACE|EXIT_SCOPE|reviewEvacuationLights|evacuation-light review complete\n");
}

inline void renderProjectionPreview(ProjectionRig& rig, ExhibitBrief& brief)
{
    std::fprintf(stderr, "TRACE|ENTER_SCOPE|renderProjectionPreview|rendering gallery preview\n");
    museumAudit().push_back("render:" + rig.label() + "->" + brief.label());
    std::fprintf(stderr, "TRACE|EXIT_SCOPE|renderProjectionPreview|gallery preview rendered\n");
}

inline void announceExhibitReady(ExhibitBrief& brief)
{
    std::fprintf(stderr, "TRACE|ENTER_SCOPE|announceExhibitReady|announcing gallery readiness\n");
    museumAudit().push_back("announce:" + brief.label());
    std::fprintf(stderr, "TRACE|EXIT_SCOPE|announceExhibitReady|gallery readiness announced\n");
}
