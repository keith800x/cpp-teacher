#include <cassert>
#include <iostream>
#include <string>

int main() {
    std::cerr << "TRACE|ENTER_SCOPE|verifyArrivalBoard|" << '\n';

    Shuttle harborLoop("Harbor terminal");
    std::cerr << "TRACE|CREATE_OBJECT|harborLoop|type=Shuttle|value=destination_=Harbor terminal" << '\n';

    ArrivalBoard board;
    std::cerr << "TRACE|CREATE_OBJECT|board|type=ArrivalBoard|pointer=watched_" << '\n';
    std::cerr << "TRACE|SET_NULL|board.watched_|pointer cleared" << '\n';

    assert(!board.isWatching());
    assert(board.currentDestination() == "No shuttle selected");

    std::cerr << "TRACE|ENTER_SCOPE|watch|" << '\n';
    board.watch(harborLoop);

    if (board.isWatching() && board.currentDestination() == "Harbor terminal") {
        std::cerr << "TRACE|BIND_POINTER|board.watched_|harborLoop" << '\n';
    } else {
        std::cerr << "TRACE|SET_NULL|board.watched_|pointer cleared" << '\n';
    }
    std::cerr << "TRACE|EXIT_SCOPE|watch|" << '\n';

    assert(board.isWatching());
    assert(board.currentDestination() == "Harbor terminal");

    std::cerr << "TRACE|ENTER_SCOPE|setDestination|" << '\n';
    harborLoop.setDestination("Museum district");
    std::cerr << "TRACE|WRITE_VALUE|harborLoop|value=destination_=Museum district" << '\n';
    std::cerr << "TRACE|EXIT_SCOPE|setDestination|" << '\n';

    assert(board.currentDestination() == "Museum district");

    std::cerr << "TRACE|EXIT_SCOPE|verifyArrivalBoard|" << '\n';
    return 0;
}
