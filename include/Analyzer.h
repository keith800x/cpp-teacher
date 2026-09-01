#pragma once

#include "Exercise.h"

#include <string>
#include <vector>

struct ConceptCheckResult
{
    ConceptCheckSpec spec;
    bool passed = false;
    std::string detail;
};

struct AnalysisResult
{
    bool analysisSucceeded = false;
    std::string diagnostics;
    std::vector<ConceptCheckResult> checks;
};

class ClangAstAnalyzer
{
public:
    explicit ClangAstAnalyzer(std::string compiler = "clang++");

    AnalysisResult analyze(
        const Exercise& exercise,
        const std::string& sourceCode
    ) const;

private:
    std::string compiler_;
};
