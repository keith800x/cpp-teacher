#include <cassert>
#include <iostream>
#include <string>

int main() {
    std::cerr << "TRACE|ENTER_SCOPE|verifyDispatchTracker|" << '\n';

    EmergencyCall harborFire("Warehouse fire", "Harbor district");
    std::cerr << "TRACE|CREATE_OBJECT|harborFire|type=EmergencyCall|value=location_=Harbor district" << '\n';

    EmergencyCall tunnelCollision("Vehicle collision", "North tunnel");
    std::cerr << "TRACE|CREATE_OBJECT|tunnelCollision|type=EmergencyCall|value=location_=North tunnel" << '\n';

    DispatchTracker tracker;
    std::cerr << "TRACE|CREATE_OBJECT|tracker|type=DispatchTracker|pointer=watched_" << '\n';
    std::cerr << "TRACE|SET_NULL|tracker.watched_|pointer cleared" << '\n';

    const bool startsEmpty = !tracker.isWatching() &&
                             tracker.watchedLocation() == "No active call";

    std::cerr << "TRACE|ENTER_SCOPE|beginWatching|" << '\n';
    tracker.beginWatching(harborFire);
    const bool beganWatchingHarbor = tracker.isWatching() &&
                                     tracker.watchedLocation() == "Harbor district";
    if (beganWatchingHarbor) {
        std::cerr << "TRACE|BIND_POINTER|tracker.watched_|harborFire" << '\n';
    } else if (tracker.isWatching() && tracker.watchedLocation() == "North tunnel") {
        std::cerr << "TRACE|BIND_POINTER|tracker.watched_|tunnelCollision" << '\n';
    } else {
        std::cerr << "TRACE|SET_NULL|tracker.watched_|pointer cleared" << '\n';
    }
    std::cerr << "TRACE|EXIT_SCOPE|beginWatching|" << '\n';

    harborFire.updateLocation("Pier 6 warehouse");
    std::cerr << "TRACE|WRITE_VALUE|harborFire|value=location_=Pier 6 warehouse" << '\n';
    const bool followsHarborUpdate = tracker.isWatching() &&
                                     tracker.watchedLocation() == "Pier 6 warehouse";

    std::cerr << "TRACE|ENTER_SCOPE|switchTo|" << '\n';
    tracker.switchTo(tunnelCollision);
    const bool switchedToTunnel = tracker.isWatching() &&
                                  tracker.watchedLocation() == "North tunnel";
    if (switchedToTunnel) {
        std::cerr << "TRACE|BIND_POINTER|tracker.watched_|tunnelCollision" << '\n';
    } else if (tracker.isWatching() && tracker.watchedLocation() == "Pier 6 warehouse") {
        std::cerr << "TRACE|BIND_POINTER|tracker.watched_|harborFire" << '\n';
    } else {
        std::cerr << "TRACE|SET_NULL|tracker.watched_|pointer cleared" << '\n';
    }
    std::cerr << "TRACE|EXIT_SCOPE|switchTo|" << '\n';

    tunnelCollision.updateLocation("North tunnel east exit");
    std::cerr << "TRACE|WRITE_VALUE|tunnelCollision|value=location_=North tunnel east exit" << '\n';
    const bool followsTunnelUpdate = tracker.isWatching() &&
                                     tracker.watchedLocation() == "North tunnel east exit";

    std::cerr << "TRACE|ENTER_SCOPE|clear|" << '\n';
    tracker.clear();
    const bool cleared = !tracker.isWatching() &&
                         tracker.watchedLocation() == "No active call";
    if (cleared) {
        std::cerr << "TRACE|SET_NULL|tracker.watched_|pointer cleared" << '\n';
    } else if (tracker.watchedLocation() == "North tunnel east exit") {
        std::cerr << "TRACE|BIND_POINTER|tracker.watched_|tunnelCollision" << '\n';
    } else if (tracker.watchedLocation() == "Pier 6 warehouse") {
        std::cerr << "TRACE|BIND_POINTER|tracker.watched_|harborFire" << '\n';
    } else {
        std::cerr << "TRACE|SET_NULL|tracker.watched_|pointer cleared" << '\n';
    }
    std::cerr << "TRACE|EXIT_SCOPE|clear|" << '\n';

    assert(startsEmpty);
    assert(beganWatchingHarbor);
    assert(followsHarborUpdate);
    assert(switchedToTunnel);
    assert(followsTunnelUpdate);
    assert(cleared);

    std::cerr << "TRACE|EXIT_SCOPE|verifyDispatchTracker|" << '\n';
    return 0;
}
