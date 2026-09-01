int main()
{
    Buffer original(10);
    Buffer copy(original);

    if (original.value() != 10 || copy.value() != 10)
    {
        return 2;
    }

    copy.setValue(99);

    if (original.value() != 10)
    {
        return 3;
    }

    if (copy.value() != 99)
    {
        return 4;
    }

    return 0;
}
