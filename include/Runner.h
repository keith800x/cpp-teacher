#pragma once

#include "Compiler.h"

#include <string>

struct RunResult
{
    CompileResult compileResult;
    bool started = false;
    bool timedOut = false;
    int exitCode = -1;
    std::string stdoutText;
    std::string stderrText;
};

class ProgramRunner
{
public:
    explicit ProgramRunner(const CppCompiler& compiler);

    RunResult run(
        const std::string& sourceCode,
        const std::string& jobName,
        int timeoutSeconds = 2
    ) const;

private:
    const CppCompiler& compiler_;
};
