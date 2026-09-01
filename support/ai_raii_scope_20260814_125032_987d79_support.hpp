#include <cstdio>
#include <string>
#include <vector>

inline std::vector<std::string>& shipmentAudit()
{
    static std::vector<std::string> events;
    return events;
}

inline void resetShipmentAudit()
{
    shipmentAudit().clear();
}

inline bool shipmentAuditMatches(const std::vector<std::string>& expected)
{
    return shipmentAudit() == expected;
}

class ShipmentAsset
{
public:
    ShipmentAsset(const char* label, const char* type, int capacity)
        : label_(label),
          type_(type),
          capacity_(capacity),
          payload_(new unsigned char[static_cast<std::size_t>(capacity)]{}),
          resourceId_(nextResourceId_++)
    {
        std::fprintf(stderr, "TRACE|ENTER_SCOPE|ShipmentAsset::ShipmentAsset|%s\n", label_.c_str());
        shipmentAudit().push_back("construct:" + label_);
        std::fprintf(stderr, "TRACE|CREATE_OBJECT|%s|type=%s|pointer=payload_\n", label_.c_str(), type_.c_str());
        std::fprintf(stderr, "TRACE|ALLOCATE_RESOURCE|resource#%d|value=%d bytes\n", resourceId_, capacity_);
        std::fprintf(stderr, "TRACE|BIND_POINTER|%s.payload_|resource#%d\n", label_.c_str(), resourceId_);
        std::fprintf(stderr, "TRACE|EXIT_SCOPE|ShipmentAsset::ShipmentAsset|%s\n", label_.c_str());
    }

    ShipmentAsset(const ShipmentAsset&) = delete;
    ShipmentAsset& operator=(const ShipmentAsset&) = delete;

    ~ShipmentAsset()
    {
        std::fprintf(stderr, "TRACE|ENTER_SCOPE|ShipmentAsset::~ShipmentAsset|%s\n", label_.c_str());
        shipmentAudit().push_back("destroy:" + label_);
        std::fprintf(stderr, "TRACE|DESTROY_BEGIN|%s|shipment asset cleanup begins\n", label_.c_str());
        delete[] payload_;
        payload_ = nullptr;
        std::fprintf(stderr, "TRACE|FREE_RESOURCE|resource#%d|shipment asset released\n", resourceId_);
        std::fprintf(stderr, "TRACE|DESTROY_END|%s|shipment asset cleanup completed\n", label_.c_str());
        std::fprintf(stderr, "TRACE|EXIT_SCOPE|ShipmentAsset::~ShipmentAsset|%s\n", label_.c_str());
    }

    const std::string& label() const
    {
        return label_;
    }

private:
    inline static int nextResourceId_ = 1;

    std::string label_;
    std::string type_;
    int capacity_;
    unsigned char* payload_;
    int resourceId_;
};

class DispatchRecord : public ShipmentAsset
{
public:
    explicit DispatchRecord(const char* label)
        : ShipmentAsset(label, "DispatchRecord", 128)
    {
    }
};

class ColdPack : public ShipmentAsset
{
public:
    explicit ColdPack(const char* label)
        : ShipmentAsset(label, "ColdPack", 256)
    {
    }
};

class SecuritySeal : public ShipmentAsset
{
public:
    explicit SecuritySeal(const char* label)
        : ShipmentAsset(label, "SecuritySeal", 64)
    {
    }
};

inline void chillCargo(const ColdPack& gelPack)
{
    std::fprintf(stderr, "TRACE|ENTER_SCOPE|chillCargo|preparing cargo with %s\n", gelPack.label().c_str());
    shipmentAudit().push_back("chill:" + gelPack.label());
    std::fprintf(stderr, "TRACE|EXIT_SCOPE|chillCargo|preparation complete\n");
}

inline void verifySeal(const SecuritySeal& securitySeal)
{
    std::fprintf(stderr, "TRACE|ENTER_SCOPE|verifySeal|checking %s\n", securitySeal.label().c_str());
    shipmentAudit().push_back("seal:" + securitySeal.label());
    std::fprintf(stderr, "TRACE|EXIT_SCOPE|verifySeal|seal verified\n");
}

inline void scheduleCourier(const DispatchRecord& dispatchRecord)
{
    std::fprintf(stderr, "TRACE|ENTER_SCOPE|scheduleCourier|using %s\n", dispatchRecord.label().c_str());
    shipmentAudit().push_back("schedule:" + dispatchRecord.label());
    std::fprintf(stderr, "TRACE|EXIT_SCOPE|scheduleCourier|courier scheduled\n");
}
