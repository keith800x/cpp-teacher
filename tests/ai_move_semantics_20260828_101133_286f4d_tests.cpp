#include <iostream>
#include <utility>

int main()
{
    int failureCode = 0;

    std::cerr << "TRACE|ENTER_SCOPE|supply-handoff|loading crew sends kit\n";
    std::cerr << "TRACE|CREATE_OBJECT|loadingKit|type=FieldKit\n";

    {
        FieldKit loadingKit(24);

        if (loadingKit.empty() || loadingKit.packages() != 24)
        {
            failureCode = 2;
            std::cerr << "TRACE|WARNING|loadingKit|new kit does not report 24 packages\n";
        }

        std::cerr << "TRACE|ENTER_SCOPE|FieldKit|medical station receives kit\n";
        std::cerr << "TRACE|BIND_ALIAS|other|target=loadingKit\n";
        std::cerr << "TRACE|CREATE_OBJECT|stationKit|type=FieldKit\n";

        {
            FieldKit stationKit(std::move(loadingKit));

            const bool stationReceivedPackages =
                !stationKit.empty() && stationKit.packages() == 24;
            const bool loadingKitIsEmpty =
                loadingKit.empty() && loadingKit.packages() == 0;

            if (stationReceivedPackages)
            {
                std::cerr << "TRACE|TRANSFER_VALUE|loadingKit.load_|stationKit.load_|packages=24\n";
            }
            else
            {
                std::cerr << "TRACE|WARNING|stationKit|medical station did not receive 24 packages\n";
                if (failureCode == 0)
                {
                    failureCode = 3;
                }
            }

            if (loadingKitIsEmpty)
            {
                std::cerr << "TRACE|CLEAR_VALUE|loadingKit.load_|packages=0\n";
            }
            else
            {
                std::cerr << "TRACE|WARNING|loadingKit|loading kit still reports packages\n";
                if (failureCode == 0)
                {
                    failureCode = 4;
                }
            }

            std::cerr << "TRACE|DESTROY_BEGIN|stationKit|medical station kit leaves scope\n";
        }

        std::cerr << "TRACE|DESTROY_END|stationKit|medical station kit destroyed\n";
        std::cerr << "TRACE|EXIT_SCOPE|FieldKit|medical station received kit\n";
        std::cerr << "TRACE|DESTROY_BEGIN|loadingKit|loading kit leaves scope\n";
    }

    std::cerr << "TRACE|DESTROY_END|loadingKit|loading kit destroyed\n";
    std::cerr << "TRACE|EXIT_SCOPE|supply-handoff|handoff complete\n";

    return failureCode;
}
