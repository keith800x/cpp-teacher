#include <cstdio>
#include <string>
#include <vector>

inline std::vector<std::string>& harborAudit()
{
    static std::vector<std::string> events;
    return events;
}

inline void resetHarborAudit()
{
    harborAudit().clear();
}

inline bool harborAuditMatches(const std::vector<std::string>& expected)
{
    return harborAudit() == expected;
}

class BulletinPacket
{
public:
    explicit BulletinPacket(const char* label)
        : label_(label)
    {
        harborAudit().push_back("create:" + label_);
        std::fprintf(stderr, "TRACE|CREATE_OBJECT|%s|type=BulletinPacket\n", label_.c_str());
    }

    ~BulletinPacket()
    {
        harborAudit().push_back("destroy:" + label_);
        std::fprintf(stderr, "TRACE|DESTROY_BEGIN|%s|BulletinPacket cleanup begins\n", label_.c_str());
        std::fprintf(stderr, "TRACE|DESTROY_END|%s|BulletinPacket cleanup completed\n", label_.c_str());
    }

    const std::string& label() const
    {
        return label_;
    }

private:
    std::string label_;
};

class TideGaugeSession
{
public:
    explicit TideGaugeSession(const char* label)
        : label_(label), resourceId_(nextResourceId_++)
    {
        harborAudit().push_back("open:" + label_);
        std::fprintf(stderr, "TRACE|CREATE_OBJECT|%s|type=TideGaugeSession\n", label_.c_str());
        std::fprintf(stderr, "TRACE|ALLOCATE_RESOURCE|resource#%d|value=tide-gauge channel\n", resourceId_);
        std::fprintf(stderr, "TRACE|BIND_POINTER|%s.channel_|resource#%d\n", label_.c_str(), resourceId_);
    }

    TideGaugeSession(const TideGaugeSession&) = delete;
    TideGaugeSession& operator=(const TideGaugeSession&) = delete;

    ~TideGaugeSession()
    {
        harborAudit().push_back("close:" + label_);
        std::fprintf(stderr, "TRACE|DESTROY_BEGIN|%s|TideGaugeSession cleanup begins\n", label_.c_str());
        std::fprintf(stderr, "TRACE|FREE_RESOURCE|resource#%d|tide-gauge channel closed\n", resourceId_);
        std::fprintf(stderr, "TRACE|DESTROY_END|%s|TideGaugeSession cleanup completed\n", label_.c_str());
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

inline void captureTideReadings(TideGaugeSession& session, BulletinPacket& bulletin)
{
    std::fprintf(stderr, "TRACE|ENTER_SCOPE|captureTideReadings|collecting harbor readings\n");
    harborAudit().push_back("capture:" + session.label() + "->" + bulletin.label());
    std::fprintf(stderr, "TRACE|EXIT_SCOPE|captureTideReadings|readings collected\n");
}

inline void radioTransmit(BulletinPacket& bulletin)
{
    std::fprintf(stderr, "TRACE|ENTER_SCOPE|radioTransmit|broadcasting harbor bulletin\n");
    harborAudit().push_back("transmit:" + bulletin.label());
    std::fprintf(stderr, "TRACE|EXIT_SCOPE|radioTransmit|broadcast completed\n");
}
