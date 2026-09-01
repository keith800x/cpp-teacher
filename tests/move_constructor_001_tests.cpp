#include <utility>

int main()
{
    Buffer source(42);
    Buffer destination(std::move(source));

    if (destination.empty())
    {
        return 2;
    }

    if (destination.value() != 42)
    {
        return 3;
    }

    if (!source.empty())
    {
        return 4;
    }

    return 0;
}
