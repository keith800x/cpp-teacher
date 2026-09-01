#include "Grader.h"

#include <fstream>
#include <sstream>
#include <stdexcept>

namespace
{
std::string readEntireFile(const std::string& path)
{
    std::ifstream file(path);

    if (!file)
    {
        throw std::runtime_error(
            "Could not open hidden test file: " + path
        );
    }

    std::ostringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}
}

ExerciseGrader::ExerciseGrader(
    const ProgramRunner& runner,
    const ClangAstAnalyzer& analyzer
)
    : runner_(runner),
      analyzer_(analyzer)
{
}

std::string ExerciseGrader::buildSourceForGrading(
    const Exercise& exercise,
    const std::string& studentCode,
    GradeResult& result
) const
{
    std::string source;

    if (exercise.getSupportFile().has_value())
    {
        source +=
            readEntireFile(exercise.getSupportFile().value()) +
            "\n\n";
    }

    source += studentCode;

    if (exercise.getHiddenTestFile().has_value())
    {
        result.hiddenTestsUsed = true;

        source +=
            "\n\n" +
            readEntireFile(
                exercise.getHiddenTestFile().value()
            );
    }

    return source;
}

GradeResult ExerciseGrader::grade(
    const Exercise& exercise,
    const std::string& studentCode
) const
{
    GradeResult result;

    const std::string sourceToRun =
        buildSourceForGrading(exercise, studentCode, result);

    result.runResult =
        runner_.run(sourceToRun, "student_submission");

    if (!result.runResult.compileResult.success)
    {
        result.hiddenTestsPassed = false;
        result.semanticChecksPassed = false;
        return result;
    }

    if (!result.runResult.started ||
        result.runResult.timedOut)
    {
        result.hiddenTestsPassed = false;
        result.semanticChecksPassed = false;
        return result;
    }

    if (result.hiddenTestsUsed)
    {
        result.hiddenTestsPassed =
            (result.runResult.exitCode == 0);
    }

    if (exercise.getExpectedOutput().has_value())
    {
        result.outputMatches =
            result.runResult.stdoutText ==
            exercise.getExpectedOutput().value();
    }

    for (const std::string& required :
         exercise.getRequiredCodeFragments())
    {
        if (studentCode.find(required) == std::string::npos)
        {
            result.missingLegacyRequirements.push_back(required);
        }
    }

    std::string analysisSource;

    if (exercise.getAnalysisSupportFile().has_value())
    {
        analysisSource =
            readEntireFile(
                exercise.getAnalysisSupportFile().value()
            ) +
            "\n\n";
    }

    analysisSource += studentCode;

    result.analysisResult =
        analyzer_.analyze(exercise, analysisSource);

    if (!exercise.getConceptChecks().empty())
    {
        result.semanticChecksPassed =
            result.analysisResult.analysisSucceeded;

        for (const ConceptCheckResult& check :
             result.analysisResult.checks)
        {
            if (!check.passed)
            {
                result.semanticChecksPassed = false;
            }
        }
    }

    result.passed =
        result.runResult.compileResult.success &&
        result.runResult.started &&
        !result.runResult.timedOut &&
        result.runResult.exitCode == 0 &&
        result.hiddenTestsPassed &&
        result.outputMatches &&
        result.missingLegacyRequirements.empty() &&
        result.semanticChecksPassed;

    return result;
}
