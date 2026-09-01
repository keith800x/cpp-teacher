class TrackedResource
{
public:
    explicit TrackedResource(int);
    ~TrackedResource();

    int value() const;
    int id() const;
};
