#include "Exercise.h"

#include <fstream>
#include <iostream>
#include <stdexcept>
#include <utility>

#include <nlohmann/json.hpp>

using json = nlohmann::json;

Exercise Exercise::loadFromFile(const std::string& path)
{
    std::ifstream file(path);

    if (!file)
    {
        throw std::runtime_error("Could not open exercise file: " + path);
    }

    json data;
    file >> data;

    Exercise exercise;

    exercise.id_ = data.at("id").get<std::string>();
    exercise.topic_ = data.at("topic").get<std::string>();
    exercise.title_ = data.at("title").get<std::string>();
    const json& difficulty =
        data.at("difficulty");

    if (difficulty.is_string())
    {
        exercise.difficulty_ =
            difficulty.get<std::string>();
    }
    else if (difficulty.is_number_integer())
    {
        const int legacyDifficulty =
            difficulty.get<int>();

        if (legacyDifficulty <= 1)
        {
            exercise.difficulty_ = "easy";
        }
        else if (legacyDifficulty == 2)
        {
            exercise.difficulty_ = "medium";
        }
        else
        {
            exercise.difficulty_ = "hard";
        }
    }
    else
    {
        throw std::runtime_error(
            "Exercise difficulty must be easy, medium, hard, or a legacy integer."
        );
    }

    if (exercise.difficulty_ != "easy" &&
        exercise.difficulty_ != "medium" &&
        exercise.difficulty_ != "hard")
    {
        throw std::runtime_error(
            "Exercise difficulty must be easy, medium, or hard."
        );
    }
    exercise.type_ = data.at("type").get<std::string>();
    exercise.learningObjective_ =
        data.at("learning_objective").get<std::string>();
    exercise.instructions_ =
        data.at("instructions").get<std::string>();
    exercise.starterCode_ =
        data.at("starter_code").get<std::string>();
    exercise.referenceSolution_ =
        data.at("reference_solution").get<std::string>();
    exercise.expectedConcepts_ =
        data.at("expected_concepts").get<std::vector<std::string>>();
    exercise.requiredCodeFragments_ =
        data.value("required_code_fragments", std::vector<std::string>{});
    exercise.hints_ =
        data.at("hints").get<std::vector<std::string>>();
    exercise.explanation_ =
        data.at("explanation").get<std::string>();

    if (data.contains("concept_checks"))
    {
        for (const auto& item : data.at("concept_checks"))
        {
            ConceptCheckSpec check;
            check.type = item.at("type").get<std::string>();
            check.functionName = item.value("function", "");
            check.parameterName = item.value("parameter", "");
            check.variableName = item.value("variable", "");
            check.argumentName = item.value("argument", "");
            check.className = item.value("class", "");
            exercise.conceptChecks_.push_back(std::move(check));
        }
    }

    if (data.contains("expected_output"))
    {
        exercise.expectedOutput_ =
            data.at("expected_output").get<std::string>();
    }

    if (data.contains("hidden_test_file"))
    {
        exercise.hiddenTestFile_ =
            data.at("hidden_test_file").get<std::string>();
    }

    if (data.contains("support_file"))
    {
        exercise.supportFile_ =
            data.at("support_file").get<std::string>();
    }

    if (data.contains("analysis_support_file"))
    {
        exercise.analysisSupportFile_ =
            data.at("analysis_support_file").get<std::string>();
    }

    exercise.traceMode_ =
        data.value("trace_mode", std::string("source_pattern"));

    return exercise;
}

void Exercise::print() const
{
    std::cout << "\n========================================\n";
    std::cout << "          C++ TEACHER - EXERCISE\n";
    std::cout << "========================================\n\n";

    std::cout << "Title:      " << title_ << '\n';
    std::cout << "Topic:      " << topic_ << '\n';
    std::cout << "Difficulty: " << difficulty_ << '\n';
    std::cout << "Type:       " << type_ << "\n\n";

    std::cout << "Learning objective:\n";
    std::cout << learningObjective_ << "\n\n";

    std::cout << "Instructions:\n";
    std::cout << instructions_ << "\n\n";

    std::cout << "Starter code:\n";
    std::cout << "----------------------------------------\n";
    std::cout << starterCode_ << '\n';
    std::cout << "----------------------------------------\n";

    if (!conceptChecks_.empty())
    {
        std::cout << "\nSemantic checks: enabled (Clang AST)\n";
    }

    if (hiddenTestFile_.has_value())
    {
        std::cout << "Hidden tests:    enabled\n";
    }
}

const std::string& Exercise::getId() const { return id_; }
const std::string& Exercise::getTopic() const { return topic_; }
const std::string& Exercise::getTitle() const { return title_; }
const std::string& Exercise::getDifficulty() const { return difficulty_; }
const std::string& Exercise::getType() const { return type_; }
const std::string& Exercise::getLearningObjective() const { return learningObjective_; }
const std::string& Exercise::getInstructions() const { return instructions_; }
const std::string& Exercise::getStarterCode() const { return starterCode_; }
const std::string& Exercise::getReferenceSolution() const { return referenceSolution_; }
const std::vector<std::string>& Exercise::getExpectedConcepts() const { return expectedConcepts_; }
const std::vector<std::string>& Exercise::getRequiredCodeFragments() const { return requiredCodeFragments_; }
const std::vector<ConceptCheckSpec>& Exercise::getConceptChecks() const { return conceptChecks_; }
const std::vector<std::string>& Exercise::getHints() const { return hints_; }
const std::string& Exercise::getExplanation() const { return explanation_; }
const std::optional<std::string>& Exercise::getExpectedOutput() const { return expectedOutput_; }
const std::optional<std::string>& Exercise::getHiddenTestFile() const { return hiddenTestFile_; }

const std::optional<std::string>& Exercise::getSupportFile() const
{
    return supportFile_;
}

const std::optional<std::string>& Exercise::getAnalysisSupportFile() const
{
    return analysisSupportFile_;
}

const std::string& Exercise::getTraceMode() const
{
    return traceMode_;
}
