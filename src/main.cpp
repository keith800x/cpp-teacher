#include "Analyzer.h"
#include "Compiler.h"
#include "Exercise.h"
#include "Grader.h"
#include "GradeReportSerializer.h"
#include "MemoryStateBuilder.h"
#include "MemoryStatePrinter.h"
#include "MemoryTimelineSerializer.h"
#include "Runner.h"
#include "RuntimeTraceParser.h"
#include "TraceBuilder.h"
#include "TimelineManifestWriter.h"

#include <exception>
#include <filesystem>
#include <iostream>
#include <sstream>
#include <string>

namespace
{
std::string readAllStudentCode()
{
    std::ostringstream code;
    code << std::cin.rdbuf();
    return code.str();
}

std::string readStudentCode()
{
    std::cout
        << "\nPaste your C++ solution below.\n"
        << "When you are finished, type END on a line by itself.\n\n";

    std::ostringstream code;
    std::string line;

    while (std::getline(std::cin, line))
    {
        if (line == "END")
        {
            break;
        }

        code << line << '\n';
    }

    return code.str();
}

void printGradeResult(
    const Exercise& exercise,
    const GradeResult& result
)
{
    std::cout << "\n========================================\n";
    std::cout << "              RESULT\n";
    std::cout << "========================================\n\n";

    if (!result.runResult.compileResult.success)
    {
        std::cout << "Your code did not compile.\n\n";
        std::cout << result.runResult.compileResult.diagnostics;
        return;
    }

    if (result.runResult.timedOut)
    {
        std::cout << "Your program exceeded the time limit.\n";
        return;
    }

    if (result.hiddenTestsUsed && !result.hiddenTestsPassed)
    {
        std::cout << "Your solution failed a hidden test.\n";

        if (!result.runResult.stderrText.empty())
        {
            std::cout << "\nRuntime/test stderr:\n";
            std::cout << result.runResult.stderrText;
        }
    }

    if (!exercise.getConceptChecks().empty() &&
        result.analysisResult.analysisSucceeded)
    {
        std::cout << "\nClang AST semantic checks:\n";

        for (const ConceptCheckResult& check :
             result.analysisResult.checks)
        {
            std::cout
                << "  "
                << (check.passed ? "[PASS] " : "[FAIL] ")
                << check.detail
                << '\n';
        }
    }

    if (result.passed)
    {
        std::cout << "\nPASS\n";
    }
    else
    {
        std::cout << "\nNOT PASSED\n";
    }
}

void printTrace(const SemanticTrace& trace)
{
    if (trace.events.empty())
    {
        return;
    }

    std::cout << "\n========================================\n";
    std::cout << "          SEMANTIC TRACE\n";
    std::cout << "========================================\n\n";

    int step = 1;

    for (const TraceEvent& event : trace.events)
    {
        std::cout
            << step++ << ". "
            << toString(event.type)
            << " | "
            << event.subject
            << "\n   "
            << event.detail
            << "\n";
    }
}
}

int main(int argc, char* argv[])
{
    bool jsonMode = false;

    std::string exercisePath =
        "exercises/references_alias_001.json";

    for (int index = 1;
         index < argc;
         ++index)
    {
        const std::string argument =
            argv[index];

        if (argument == "--grade-json")
        {
            jsonMode = true;
        }
        else
        {
            exercisePath = argument;
        }
    }

    try
    {
        Exercise exercise =
            Exercise::loadFromFile(exercisePath);

        if (!jsonMode)
        {
            exercise.print();
        }

        CppCompiler compiler("clang++");
        ProgramRunner runner(compiler);
        ClangAstAnalyzer analyzer("clang++");
        ExerciseGrader grader(runner, analyzer);
        GradeReportSerializer gradeReportSerializer;
        TraceBuilder traceBuilder;
        RuntimeTraceParser runtimeTraceParser;
        MemoryStateBuilder memoryStateBuilder;
        MemoryStatePrinter memoryStatePrinter;
        MemoryTimelineSerializer timelineSerializer;
        TimelineManifestWriter manifestWriter;

        const std::string studentCode =
            jsonMode
                ? readAllStudentCode()
                : readStudentCode();

        if (studentCode.empty())
        {
            if (jsonMode)
            {
                std::cout
                    << "{\n"
                    << "  \"grade_schema_version\": 1,\n"
                    << "  \"exercise_id\": \""
                    << exercise.getId()
                    << "\",\n"
                    << "  \"passed\": false,\n"
                    << "  \"error\": \"No code submitted.\"\n"
                    << "}\n";
            }
            else
            {
                std::cout
                    << "\nNo code submitted.\n";
            }

            return 0;
        }

        const GradeResult result =
            grader.grade(
                exercise,
                studentCode
            );

        if (!jsonMode)
        {
            printGradeResult(
                exercise,
                result
            );
        }

        SemanticTrace trace;

        if (exercise.getTraceMode() == "runtime" ||
            exercise.getTraceMode() == "runtime_derived_raii")
        {
            const SemanticTrace runtimeTrace =
                runtimeTraceParser.parse(
                    result.runResult.stderrText
                );

            trace =
                traceBuilder.deriveRuntimeTrace(
                    exercise,
                    runtimeTrace,
                    result.passed
                );
        }
        else
        {
            trace =
                traceBuilder.build(
                    exercise,
                    studentCode
                );
        }

        if (!jsonMode)
        {
            printTrace(trace);
        }

        const MemoryTimeline timeline =
            memoryStateBuilder.build(trace);

        if (!jsonMode)
        {
            memoryStatePrinter.print(timeline);
        }

        const std::filesystem::path timelinePath =
            std::filesystem::path("output") /
            (
                exercise.getId() +
                "_memory_timeline.json"
            );

        timelineSerializer.writeJsonFile(
            timeline,
            exercise.getId(),
            timelinePath
        );

        const std::filesystem::path manifestPath =
            std::filesystem::path("output") /
            "timelines_manifest.json";

        manifestWriter.rebuild(
            "output",
            "exercises",
            manifestPath
        );

        if (jsonMode)
        {
            std::cout
                << gradeReportSerializer.toJsonString(
                       exercise,
                       result
                   )
                << '\n';
        }
        else
        {
            std::cout
                << "\nTimeline JSON written to: "
                << timelinePath.string()
                << "\n";

            std::cout
                << "Timeline manifest written to: "
                << manifestPath.string()
                << "\n";
        }
    }
    catch (const std::exception& error)
    {
        if (jsonMode)
        {
            std::cerr
                << "Structured grading error: "
                << error.what()
                << '\n';
        }
        else
        {
            std::cerr
                << "Error: "
                << error.what()
                << '\n';
        }

        return 1;
    }

    return 0;
}
