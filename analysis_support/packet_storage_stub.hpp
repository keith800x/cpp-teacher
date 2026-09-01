#include <cstddef>

class PacketStorage
{
public:
    explicit PacketStorage(std::size_t);

    PacketStorage(
        const PacketStorage&
    ) = delete;

    PacketStorage& operator=(
        const PacketStorage&
    ) = delete;

    ~PacketStorage();

    std::size_t bytes() const noexcept;
    int id() const noexcept;
};
