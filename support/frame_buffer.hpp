#include <algorithm>
#include <cstddef>
#include <cstdio>
#include <string>
#include <utility>
#include <vector>

inline std::vector<std::string>&
frameBufferAudit()
{
    static std::vector<std::string> events;
    return events;
}

inline void resetFrameBufferAudit()
{
    frameBufferAudit().clear();
}

inline bool frameBufferAuditMatches(
    const std::vector<std::string>& expected
)
{
    return frameBufferAudit() == expected;
}

class FrameBuffer
{
public:
    FrameBuffer(
        const char* label,
        int width,
        int height
    )
        : label_(label),
          width_(width),
          height_(height),
          byteCount_(
              static_cast<std::size_t>(width) *
              static_cast<std::size_t>(height)
          ),
          data_(new unsigned char[byteCount_]{}),
          resourceId_(nextResourceId_++)
    {
        frameBufferAudit().push_back(
            "construct:" + label_
        );

        std::fprintf(
            stderr,
            "TRACE|CREATE_OBJECT|%s|type=FrameBuffer\n",
            label_.c_str()
        );

        std::fprintf(
            stderr,
            "TRACE|ALLOCATE_RESOURCE|resource#%d|value=%dx%d\n",
            resourceId_,
            width_,
            height_
        );

        std::fprintf(
            stderr,
            "TRACE|BIND_POINTER|%s.data_|resource#%d\n",
            label_.c_str(),
            resourceId_
        );
    }

    FrameBuffer(const FrameBuffer&) = delete;
    FrameBuffer& operator=(const FrameBuffer&) = delete;

    ~FrameBuffer()
    {
        frameBufferAudit().push_back(
            "destroy:" + label_
        );

        std::fprintf(
            stderr,
            "TRACE|DESTROY_BEGIN|%s|FrameBuffer destructor begins\n",
            label_.c_str()
        );

        delete[] data_;
        data_ = nullptr;

        std::fprintf(
            stderr,
            "TRACE|FREE_RESOURCE|resource#%d|frame memory released\n",
            resourceId_
        );

        std::fprintf(
            stderr,
            "TRACE|DESTROY_END|%s|FrameBuffer destructor completed\n",
            label_.c_str()
        );
    }

    const std::string& label() const
    {
        return label_;
    }

private:
    inline static int nextResourceId_ = 1;

    std::string label_;
    int width_;
    int height_;
    std::size_t byteCount_;
    unsigned char* data_;
    int resourceId_;
};

inline void decodeFrame(
    FrameBuffer& buffer
)
{
    frameBufferAudit().push_back(
        "decode:" + buffer.label()
    );
}

inline void applyFilter(
    FrameBuffer& buffer
)
{
    frameBufferAudit().push_back(
        "filter:" + buffer.label()
    );
}

inline void uploadFrame(
    FrameBuffer& buffer
)
{
    frameBufferAudit().push_back(
        "upload:" + buffer.label()
    );
}
