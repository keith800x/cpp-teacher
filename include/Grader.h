#pragma once

#include "Analyzer.h"
#include "Exercise.h"
#include "Runner.h"

#include <string>
#include <vector>

struct GradeResult
{
    bool passed = false;
    RunResult runResult;
    AnalysisResult analysisResult;

    std::vector<std::string> missingLegacyRequirements;

    bool outputMatches = true;
    bool hiddenTestsUsed = false;
    bool hiddenTestsPassed = true;
    bool semanticChecksPassed = true;
};

class ExerciseGrader
{
public:
    ExerciseGrader(
        const ProgramRunner& runner,
        const ClangAstAnalyzer& analyzer
    );

    GradeResult grade(
        const Exercise& exercise,
        const std::string& studentCode
    ) const;

private:
    std::string buildSourceForGrading(
        const Exercise& exercise,
        const std::string& studentCode,
        GradeResult& result
    ) const;

    const ProgramRunner& runner_;
    const ClangAstAnalyzer& analyzer_;
};
