#include "Runner.h"

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <sstream>

#include <sys/wait.h>
#include <unistd.h>

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

ProgramRunner::ProgramRunner(const CppCompiler& compiler)
    : compiler_(compiler)
{
}

RunResult ProgramRunner::run(
    const std::string& sourceCode,
    const std::string& jobName,
    int timeoutSeconds
) const
{
    namespace fs = std::filesystem;

    const fs::path dir =
        fs::temp_directory_path() /
        ("cpp_teacher_" + std::to_string(::getpid()) + "_" + jobName);

    fs::create_directories(dir);

    const fs::path sourcePath = dir / "program.cpp";
    const fs::path executablePath = dir / "program.out";
    const fs::path compilerLog = dir / "compiler.log";
    const fs::path stdoutPath = dir / "stdout.txt";
    const fs::path stderrPath = dir / "stderr.txt";

    RunResult result;
    result.compileResult =
        compiler_.compileToExecutable(
            sourceCode,
            sourcePath,
            executablePath,
            compilerLog
        );

    if (!result.compileResult.success)
    {
        std::error_code ignored;
        fs::remove_all(dir, ignored);
        return result;
    }

    const std::string command =
        "timeout " + std::to_string(timeoutSeconds) + "s " +
        shellQuote(executablePath.string()) +
        " > " + shellQuote(stdoutPath.string()) +
        " 2> " + shellQuote(stderrPath.string());

    const int rawStatus = std::system(command.c_str());

    result.started = (rawStatus != -1);
    result.stdoutText = readEntireFile(stdoutPath);
    result.stderrText = readEntireFile(stderrPath);

    if (rawStatus != -1 && WIFEXITED(rawStatus))
    {
        result.exitCode = WEXITSTATUS(rawStatus);
        result.timedOut = (result.exitCode == 124);
    }

    std::error_code ignored;
    fs::remove_all(dir, ignored);

    return result;
}
