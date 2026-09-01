#include <cstddef>
#include <cstdio>

class PacketStorage
{
public:
    explicit PacketStorage(
        std::size_t bytes
    )
        : id_(nextId_++),
          bytes_(bytes),
          data_(new unsigned char[bytes_] {})
    {
        std::fprintf(
            stderr,
            "TRACE|ALLOCATE_RESOURCE|resource#%d|value=%zu bytes\n",
            id_,
            bytes_
        );
    }

    PacketStorage(
        const PacketStorage&
    ) = delete;

    PacketStorage& operator=(
        const PacketStorage&
    ) = delete;

    ~PacketStorage()
    {
        delete[] data_;
        data_ = nullptr;

        std::fprintf(
            stderr,
            "TRACE|FREE_RESOURCE|resource#%d|packet payload released\n",
            id_
        );
    }

    std::size_t bytes() const noexcept
    {
        return bytes_;
    }

    int id() const noexcept
    {
        return id_;
    }

private:
    inline static int nextId_ = 1;

    int id_;
    std::size_t bytes_;
    unsigned char* data_;
};
