#pragma once

#include <filesystem>
#include <string>

struct CompileResult
{
    bool success = false;
    int exitCode = -1;
    std::string diagnostics;
};

class CppCompiler
{
public:
    explicit CppCompiler(std::string compiler = "clang++");

    CompileResult compileToExecutable(
        const std::string& sourceCode,
        const std::filesystem::path& sourcePath,
        const std::filesystem::path& executablePath,
        const std::filesystem::path& diagnosticsPath
    ) const;

private:
    std::string compiler_;
};
