int main()
{
    int first = 10;
    setToTwenty(first);

    if (first != 20)
    {
        return 2;
    }

    int second = -5;
    setToTwenty(second);

    if (second != 20)
    {
        return 3;
    }

    return 0;
}
