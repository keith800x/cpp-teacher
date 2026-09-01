#include <cassert>
#include <iostream>
#include <string>

int main() {
    std::cerr << "TRACE|ENTER_SCOPE|verifyGardenFocus|" << '\n';

    Plant springMint("Spring mint");
    std::cerr << "TRACE|CREATE_OBJECT|springMint|type=Plant|value=Spring mint" << '\n';

    GardenDisplay display;
    std::cerr << "TRACE|CREATE_OBJECT|display|type=GardenDisplay|pointer=focused_" << '\n';
    std::cerr << "TRACE|SET_NULL|display.focused_|" << '\n';

    assert(!display.hasFocus());
    assert(display.focusedLabel() == "No plant selected");

    std::cerr << "TRACE|ENTER_SCOPE|highlight|" << '\n';
    display.highlight(springMint);

    if (display.hasFocus() && display.focusedLabel() == "Spring mint") {
        std::cerr << "TRACE|BIND_POINTER|display.focused_|springMint" << '\n';
    } else {
        std::cerr << "TRACE|SET_NULL|display.focused_|" << '\n';
    }
    std::cerr << "TRACE|EXIT_SCOPE|highlight|" << '\n';

    assert(display.hasFocus());
    assert(display.focusedLabel() == "Spring mint");

    springMint.rename("Lemon mint");
    assert(display.focusedLabel() == "Lemon mint");

    std::cerr << "TRACE|EXIT_SCOPE|verifyGardenFocus|" << '\n';
    return 0;
}
