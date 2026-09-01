#include "Compiler.h"

#include <cstdlib>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <utility>

#include <sys/wait.h>

namespace
{
std::string readEntireFile(const std::filesystem::path& path)
{
    std::ifstream file(path);
    if (!file) return {};

    std::ostringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

std::string shellQuote(const std::string& value)
{
    std::string result = "'";

    for (char c : value)
    {
        if (c == '\'') result += "'\\''";
        else result += c;
    }

    result += "'";
    return result;
}
}

CppCompiler::CppCompiler(std::string compiler)
    : compiler_(std::move(compiler))
{
}

CompileResult CppCompiler::compileToExecutable(
    const std::string& sourceCode,
    const std::filesystem::path& sourcePath,
    const std::filesystem::path& executablePath,
    const std::filesystem::path& diagnosticsPath
) const
{
    {
        std::ofstream file(sourcePath);
        if (!file)
        {
            throw std::runtime_error(
                "Could not create source file: " + sourcePath.string()
            );
        }
        file << sourceCode;
    }

    const std::string command =
        shellQuote(compiler_) +
        " -std=c++20 -Wall -Wextra -pedantic " +
        shellQuote(sourcePath.string()) +
        " -o " +
        shellQuote(executablePath.string()) +
        " > " +
        shellQuote(diagnosticsPath.string()) +
        " 2>&1";

    const int rawStatus = std::system(command.c_str());

    CompileResult result;
    result.diagnostics = readEntireFile(diagnosticsPath);

    if (rawStatus == -1)
    {
        result.exitCode = -1;
        result.success = false;
    }
    else if (WIFEXITED(rawStatus))
    {
        result.exitCode = WEXITSTATUS(rawStatus);
        result.success = (result.exitCode == 0);
    }

    return result;
}
