#include <iostream>

int main()
{
    struct TestCase
    {
        int input;
        int expected;
    };

    const TestCase tests[] = {
        {2, 4},
        {5, 25},
        {-3, 9},
        {0, 0},
        {11, 121}
    };

    for (const TestCase& test : tests)
    {
        const int actual = square(test.input);

        if (actual != test.expected)
        {
            std::cerr
                << "Hidden test failed for input "
                << test.input
                << ". Expected "
                << test.expected
                << ", got "
                << actual
                << ".\n";

            return 2;
        }
    }

    std::cout << "ALL_TESTS_PASSED\n";
    return 0;
}
