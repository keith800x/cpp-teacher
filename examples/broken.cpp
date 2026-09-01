#include <memory>

struct Player
{
};

int main()
{
    auto player = std::make_unique<Player>();
    auto second = player;

    return 0;
}
