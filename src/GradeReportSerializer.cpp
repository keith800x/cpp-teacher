#include "GradeReportSerializer.h"

#include <sstream>
#include <string>

#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace
{
std::string status(
    bool passed
)
{
    return passed ? "pass" : "fail";
}

std::string filteredRuntimeFeedback(
    const std::string& stderrText
)
{
    std::istringstream input(stderrText);
    std::ostringstream output;

    std::string line;
    bool first = true;

    while (std::getline(input, line))
    {
        if (line.rfind("TRACE|", 0) == 0)
        {
            continue;
        }

        if (!first)
        {
            output << '\n';
        }

        output << line;
        first = false;
    }

    return output.str();
}

json traceWarnings(
    const std::string& stderrText
)
{
    json warnings = json::array();

    std::istringstream input(stderrText);
    std::string line;

    while (std::getline(input, line))
    {
        if (line.rfind("TRACE|WARNING|", 0) != 0)
        {
            continue;
        }

        const std::size_t subjectStart =
            std::string("TRACE|WARNING|").size();

        const std::size_t detailSeparator =
            line.find('|', subjectStart);

        if (detailSeparator == std::string::npos)
        {
            warnings.push_back({
                {"subject", ""},
                {"detail", line}
            });

            continue;
        }

        warnings.push_back({
            {
                "subject",
                line.substr(
                    subjectStart,
                    detailSeparator - subjectStart
                )
            },
            {
                "detail",
                line.substr(
                    detailSeparator + 1
                )
            }
        });
    }

    return warnings;
}

json conceptChecksToJson(
    const AnalysisResult& analysis
)
{
    json checks = json::array();

    for (const ConceptCheckResult& check :
         analysis.checks)
    {
        checks.push_back({
            {"type", check.spec.type},
            {"passed", check.passed},
            {"detail", check.detail}
        });
    }

    return checks;
}
}

std::string GradeReportSerializer::toJsonString(
    const Exercise& exercise,
    const GradeResult& result
) const
{
    const bool compilationPassed =
        result.runResult.compileResult.success;

    const bool runtimePassed =
        compilationPassed &&
        result.runResult.started &&
        !result.runResult.timedOut &&
        result.runResult.exitCode == 0;

    const bool semanticUsed =
        !exercise.getConceptChecks().empty();

    const bool outputUsed =
        exercise.getExpectedOutput().has_value();

    const bool legacyRequirementsUsed =
        !exercise.getRequiredCodeFragments().empty();

    json semanticChecks = {
        {"used", semanticUsed},
        {"analysis_succeeded",
            result.analysisResult.analysisSucceeded},
        {"diagnostics",
            result.analysisResult.diagnostics},
        {"checks",
            conceptChecksToJson(
                result.analysisResult
            )}
    };

    if (!semanticUsed)
    {
        semanticChecks["status"] = "skipped";
        semanticChecks["passed"] = true;
    }
    else if (!compilationPassed ||
             !result.runResult.started ||
             result.runResult.timedOut)
    {
        semanticChecks["status"] = "blocked";
        semanticChecks["passed"] = false;
    }
    else
    {
        semanticChecks["status"] =
            status(
                result.semanticChecksPassed
            );

        semanticChecks["passed"] =
            result.semanticChecksPassed;
    }

    json hiddenTests = {
        {"used", result.hiddenTestsUsed},
        {"passed", result.hiddenTestsPassed}
    };

    if (!result.hiddenTestsUsed)
    {
        hiddenTests["status"] = "skipped";
    }
    else if (!compilationPassed ||
             !result.runResult.started ||
             result.runResult.timedOut)
    {
        hiddenTests["status"] = "blocked";
    }
    else
    {
        hiddenTests["status"] =
            status(
                result.hiddenTestsPassed
            );
    }

    json outputCheck = {
        {"used", outputUsed},
        {"passed", result.outputMatches}
    };

    if (!outputUsed)
    {
        outputCheck["status"] = "skipped";
    }
    else if (!runtimePassed)
    {
        outputCheck["status"] = "blocked";
    }
    else
    {
        outputCheck["status"] =
            status(
                result.outputMatches
            );
    }

    json legacyRequirements = {
        {"used", legacyRequirementsUsed},
        {
            "missing",
            result.missingLegacyRequirements
        }
    };

    if (!legacyRequirementsUsed)
    {
        legacyRequirements["status"] = "skipped";
        legacyRequirements["passed"] = true;
    }
    else
    {
        const bool requirementsPassed =
            result.missingLegacyRequirements.empty();

        legacyRequirements["status"] =
            status(requirementsPassed);

        legacyRequirements["passed"] =
            requirementsPassed;
    }

    json document = {
        {"grade_schema_version", 1},
        {"exercise_id", exercise.getId()},
        {"title", exercise.getTitle()},
        {"passed", result.passed},

        {
            "compilation",
            {
                {"status",
                    status(compilationPassed)},
                {"passed",
                    compilationPassed},
                {"exit_code",
                    result.runResult.compileResult.exitCode},
                {"diagnostics",
                    result.runResult.compileResult.diagnostics}
            }
        },

        {
            "runtime",
            {
                {"status",
                    compilationPassed
                        ? status(runtimePassed)
                        : "blocked"},
                {"passed",
                    runtimePassed},
                {"started",
                    result.runResult.started},
                {"timed_out",
                    result.runResult.timedOut},
                {"exit_code",
                    result.runResult.exitCode},
                {"stdout",
                    result.runResult.stdoutText},
                {"feedback",
                    filteredRuntimeFeedback(
                        result.runResult.stderrText
                    )},
                {"trace_warnings",
                    traceWarnings(
                        result.runResult.stderrText
                    )}
            }
        },

        {"hidden_tests", hiddenTests},
        {"semantic_checks", semanticChecks},
        {"output_check", outputCheck},
        {"legacy_requirements", legacyRequirements}
    };

    return document.dump(2);
}
