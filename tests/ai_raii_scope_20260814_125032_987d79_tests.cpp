#include <string>
#include <vector>

int main()
{
    resetShipmentAudit();
    completeShipment();

    const std::vector<std::string> expected = {
        "construct:dispatchRecord",
        "construct:gelPack",
        "construct:securitySeal",
        "chill:gelPack",
        "seal:securitySeal",
        "destroy:securitySeal",
        "destroy:gelPack",
        "schedule:dispatchRecord",
        "destroy:dispatchRecord"
    };

    return shipmentAuditMatches(expected) ? 0 : 2;
}
