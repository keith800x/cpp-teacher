#include <cassert>
#include <iostream>
#include <string>

int main() {
    std::cerr << "TRACE|ENTER_SCOPE|verifyCargoTagLifecycle|" << '\n';

    CargoTag* primary = new CargoTag("CR-17", 10);
    std::cerr << "TRACE|ALLOCATE_RESOURCE|resource#1|value=code_=CR-17,priority_=10" << '\n';

    CargoTag* replacement = new CargoTag("CR-18", 4);
    std::cerr << "TRACE|ALLOCATE_RESOURCE|resource#2|value=code_=CR-18,priority_=4" << '\n';

    DockConsole console;
    std::cerr << "TRACE|CREATE_OBJECT|console|type=DockConsole|pointer=active_" << '\n';
    std::cerr << "TRACE|SET_NULL|console.active_|pointer cleared" << '\n';

    AuditDisplay display;
    std::cerr << "TRACE|CREATE_OBJECT|display|type=AuditDisplay|pointer=watched_" << '\n';
    std::cerr << "TRACE|SET_NULL|display.watched_|pointer cleared" << '\n';

    assert(!console.hasActive());
    assert(!display.hasWatched());
    assert(console.activeCode() == "No active cargo");
    assert(display.watchedCode() == "No cargo under review");

    std::cerr << "TRACE|ENTER_SCOPE|assign|" << '\n';
    console.assign(primary);
    const bool consoleHasPrimary = console.hasActive() &&
                                   console.activeCode() == "CR-17" &&
                                   console.activePriority() == 10;
    if (consoleHasPrimary) {
        std::cerr << "TRACE|BIND_POINTER|console.active_|resource#1" << '\n';
    } else {
        std::cerr << "TRACE|SET_NULL|console.active_|pointer cleared" << '\n';
    }
    std::cerr << "TRACE|EXIT_SCOPE|assign|" << '\n';
    assert(consoleHasPrimary);

    std::cerr << "TRACE|ENTER_SCOPE|watch|" << '\n';
    display.watch(primary);
    const bool displayHasPrimary = display.hasWatched() &&
                                   display.watchedCode() == "CR-17" &&
                                   display.watchedPriority() == 10;
    if (displayHasPrimary) {
        std::cerr << "TRACE|BIND_POINTER|display.watched_|resource#1" << '\n';
    } else {
        std::cerr << "TRACE|SET_NULL|display.watched_|pointer cleared" << '\n';
    }
    std::cerr << "TRACE|EXIT_SCOPE|watch|" << '\n';
    assert(displayHasPrimary);

    std::cerr << "TRACE|ENTER_SCOPE|boostPriority|" << '\n';
    console.boostPriority(7);
    const bool sharedPriorityChanged = console.activePriority() == 17 &&
                                       display.watchedPriority() == 17;
    if (sharedPriorityChanged) {
        std::cerr << "TRACE|WRITE_VALUE|resource#1|value=code_=CR-17,priority_=17|through=console.active_" << '\n';
    }
    std::cerr << "TRACE|EXIT_SCOPE|boostPriority|" << '\n';
    assert(sharedPriorityChanged);

    std::cerr << "TRACE|ENTER_SCOPE|assign|" << '\n';
    console.assign(replacement);
    const bool consoleHasReplacement = console.hasActive() &&
                                       console.activeCode() == "CR-18" &&
                                       console.activePriority() == 4;
    if (consoleHasReplacement) {
        std::cerr << "TRACE|BIND_POINTER|console.active_|resource#2" << '\n';
    } else {
        std::cerr << "TRACE|SET_NULL|console.active_|pointer cleared" << '\n';
    }
    std::cerr << "TRACE|EXIT_SCOPE|assign|" << '\n';
    assert(consoleHasReplacement);
    assert(display.watchedCode() == "CR-17");

    std::cerr << "TRACE|ENTER_SCOPE|rename|" << '\n';
    replacement->rename("CR-18B");
    std::cerr << "TRACE|WRITE_VALUE|resource#2|value=code_=CR-18B,priority_=4" << '\n';
    std::cerr << "TRACE|EXIT_SCOPE|rename|" << '\n';
    assert(console.activeCode() == "CR-18B");

    std::cerr << "TRACE|ENTER_SCOPE|watch|" << '\n';
    display.watch(replacement);
    const bool displayReseated = display.hasWatched() &&
                                 display.watchedCode() == "CR-18B" &&
                                 display.watchedPriority() == 4;
    if (displayReseated) {
        std::cerr << "TRACE|BIND_POINTER|display.watched_|resource#2" << '\n';
    } else {
        std::cerr << "TRACE|SET_NULL|display.watched_|pointer cleared" << '\n';
    }
    std::cerr << "TRACE|EXIT_SCOPE|watch|" << '\n';
    assert(displayReseated);

    delete primary;
    std::cerr << "TRACE|FREE_RESOURCE|resource#1|CargoTag retired" << '\n';

    assert(display.watchedCode() == "CR-18B");
    assert(display.watchedPriority() == 4);

    std::cerr << "TRACE|ENTER_SCOPE|clear|" << '\n';
    console.clear();
    if (!console.hasActive()) {
        std::cerr << "TRACE|SET_NULL|console.active_|pointer cleared" << '\n';
    }
    std::cerr << "TRACE|EXIT_SCOPE|clear|" << '\n';
    assert(!console.hasActive());
    assert(console.activeCode() == "No active cargo");
    assert(console.activePriority() == -1);

    std::cerr << "TRACE|ENTER_SCOPE|clear|" << '\n';
    display.clear();
    if (!display.hasWatched()) {
        std::cerr << "TRACE|SET_NULL|display.watched_|pointer cleared" << '\n';
    }
    std::cerr << "TRACE|EXIT_SCOPE|clear|" << '\n';
    assert(!display.hasWatched());
    assert(display.watchedCode() == "No cargo under review");
    assert(display.watchedPriority() == -1);

    delete replacement;
    std::cerr << "TRACE|FREE_RESOURCE|resource#2|CargoTag retired" << '\n';

    std::cerr << "TRACE|EXIT_SCOPE|verifyCargoTagLifecycle|" << '\n';
    return 0;
}
