#pragma once

class SupplyLoad
{
public:
    explicit SupplyLoad(int packages);

    SupplyLoad(const SupplyLoad& other);
    SupplyLoad& operator=(const SupplyLoad&) = delete;

    SupplyLoad(SupplyLoad&& other) noexcept;
    SupplyLoad& operator=(SupplyLoad&&) = delete;

    ~SupplyLoad();

    int packages() const;
};
