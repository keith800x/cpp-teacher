int main()
{
    int first = 42;

    if (readValue(first) != 42)
    {
        return 2;
    }

    const int second = -7;

    if (readValue(second) != -7)
    {
        return 3;
    }

    return 0;
}
