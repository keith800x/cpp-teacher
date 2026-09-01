#include <cstdio>
#include <string>
#include <type_traits>

int main()
{
    constexpr bool shipmentUsesReference =
        std::is_same_v<
            decltype(&receiveShipment),
            void (*)(int&, int)
        >;

    constexpr bool labelUsesConstReference =
        std::is_same_v<
            decltype(&warehouseLabelLength),
            std::size_t (*)(const std::string&)
        >;

    std::fprintf(
        stderr,
        "TRACE|ENTER_SCOPE|caller|warehouse service request\n"
    );

    int stock = 10;

    std::fprintf(
        stderr,
        "TRACE|CREATE_VALUE|stock|type=int|value=%d\n",
        stock
    );

    std::fprintf(
        stderr,
        "TRACE|ENTER_SCOPE|receiveShipment|function call\n"
    );

    if constexpr (shipmentUsesReference)
    {
        std::fprintf(
            stderr,
            "TRACE|BIND_ALIAS|stockCount|target=stock|type=int&|const=false\n"
        );
    }
    else
    {
        std::fprintf(
            stderr,
            "TRACE|CREATE_VALUE|stockCount|type=int|value=%d\n",
            stock
        );

        std::fprintf(
            stderr,
            "TRACE|WARNING|stockCount|parameter is a copy; caller stock will not be updated\n"
        );
    }

    receiveShipment(stock, 15);

    std::fprintf(
        stderr,
        "TRACE|WRITE_VALUE|stock|via=receiveShipment|value=%d\n",
        stock
    );

    std::fprintf(
        stderr,
        "TRACE|EXIT_SCOPE|receiveShipment|function returned\n"
    );

    const std::string warehouseLabel =
        "East Distribution Center";

    std::fprintf(
        stderr,
        "TRACE|CREATE_VALUE|warehouseLabel|type=std::string|value=East Distribution Center\n"
    );

    std::fprintf(
        stderr,
        "TRACE|ENTER_SCOPE|warehouseLabelLength|function call\n"
    );

    if constexpr (labelUsesConstReference)
    {
        std::fprintf(
            stderr,
            "TRACE|BIND_ALIAS|label|target=warehouseLabel|type=const std::string&|const=true\n"
        );
    }
    else
    {
        std::fprintf(
            stderr,
            "TRACE|CREATE_VALUE|label|type=std::string|value=East Distribution Center\n"
        );

        std::fprintf(
            stderr,
            "TRACE|WARNING|label|parameter is copied instead of observing the existing string\n"
        );
    }

    const std::size_t length =
        warehouseLabelLength(
            warehouseLabel
        );

    std::fprintf(
        stderr,
        "TRACE|EXIT_SCOPE|warehouseLabelLength|function returned\n"
    );

    std::fprintf(
        stderr,
        "TRACE|EXIT_SCOPE|caller|warehouse service request completed\n"
    );

    if (stock != 25)
    {
        std::fprintf(
            stderr,
            "receiveShipment must update the caller's stock count. "
            "Expected 25, got %d.\n",
            stock
        );

        return 2;
    }

    if (length != warehouseLabel.size())
    {
        std::fprintf(
            stderr,
            "warehouseLabelLength returned the wrong result.\n"
        );

        return 3;
    }

    if (!shipmentUsesReference)
    {
        std::fprintf(
            stderr,
            "receiveShipment must take stockCount as a non-const lvalue reference.\n"
        );

        return 4;
    }

    if (!labelUsesConstReference)
    {
        std::fprintf(
            stderr,
            "warehouseLabelLength must take label as a const lvalue reference.\n"
        );

        return 5;
    }

    return 0;
}
