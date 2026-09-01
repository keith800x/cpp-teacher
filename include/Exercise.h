#pragma once

#include <optional>
#include <string>
#include <vector>

struct ConceptCheckSpec
{
    std::string type;

    std::string functionName;
    std::string parameterName;

    std::string variableName;
    std::string argumentName;

    std::string className;
};

class Exercise
{
public:
    static Exercise loadFromFile(const std::string& path);

    void print() const;

    const std::string& getId() const;
    const std::string& getTopic() const;
    const std::string& getTitle() const;
    const std::string& getDifficulty() const;
    const std::string& getType() const;
    const std::string& getLearningObjective() const;
    const std::string& getInstructions() const;
    const std::string& getStarterCode() const;
    const std::string& getReferenceSolution() const;
    const std::vector<std::string>& getExpectedConcepts() const;
    const std::vector<std::string>& getRequiredCodeFragments() const;
    const std::vector<ConceptCheckSpec>& getConceptChecks() const;
    const std::vector<std::string>& getHints() const;
    const std::string& getExplanation() const;
    const std::optional<std::string>& getExpectedOutput() const;
    const std::optional<std::string>& getHiddenTestFile() const;
    const std::optional<std::string>& getSupportFile() const;
    const std::optional<std::string>& getAnalysisSupportFile() const;
    const std::string& getTraceMode() const;

private:
    std::string id_;
    std::string topic_;
    std::string title_;
    std::string difficulty_ = "medium";
    std::string type_;

    std::string learningObjective_;
    std::string instructions_;
    std::string starterCode_;
    std::string referenceSolution_;

    std::vector<std::string> expectedConcepts_;
    std::vector<std::string> requiredCodeFragments_;
    std::vector<ConceptCheckSpec> conceptChecks_;
    std::vector<std::string> hints_;

    std::string explanation_;
    std::optional<std::string> expectedOutput_;
    std::optional<std::string> hiddenTestFile_;
    std::optional<std::string> supportFile_;
    std::optional<std::string> analysisSupportFile_;
    std::string traceMode_ = "source_pattern";
};
