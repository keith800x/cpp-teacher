#include <cstdio>

class TrackedResource
{
public:
    explicit TrackedResource(int value)
        : id_(nextId_++),
          value_(value)
    {
        std::fprintf(
            stderr,
            "TRACE|ALLOCATE_RESOURCE|resource#%d|value=%d\n",
            id_,
            value_
        );
    }

    ~TrackedResource()
    {
        std::fprintf(
            stderr,
            "TRACE|FREE_RESOURCE|resource#%d|resource destructor\n",
            id_
        );
    }

    int value() const
    {
        return value_;
    }

    int id() const
    {
        return id_;
    }

private:
    inline static int nextId_ = 1;

    int id_;
    int value_;
};
