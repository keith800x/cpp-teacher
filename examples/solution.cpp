#include <memory>
#include <utility>

struct Player
{
};

int main()
{
    auto player = std::make_unique<Player>();
    auto second = std::move(player);

    return 0;
}
