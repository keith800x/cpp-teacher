#pragma once

#include <iostream>

class SupplyLoad
{
public:
    explicit SupplyLoad(int packages)
        : packages_(packages)
    {
        std::cerr << "TRACE|INITIALIZE_VALUE|supply load|packages="
                  << packages_ << "\n";
    }

    SupplyLoad(const SupplyLoad& other)
        : packages_(other.packages_)
    {
        std::cerr << "TRACE|COPY_VALUE|supply load|packages="
                  << packages_ << "\n";
    }

    SupplyLoad& operator=(const SupplyLoad&) = delete;

    SupplyLoad(SupplyLoad&& other) noexcept
        : packages_(other.packages_)
    {
        other.packages_ = 0;
        std::cerr << "TRACE|MOVE_VALUE|supply load|packages="
                  << packages_ << "\n";
    }

    SupplyLoad& operator=(SupplyLoad&&) = delete;

    ~SupplyLoad()
    {
        std::cerr << "TRACE|DESTROY_VALUE|supply load|packages="
                  << packages_ << "\n";
    }

    int packages() const
    {
        return packages_;
    }

private:
    int packages_;
};
