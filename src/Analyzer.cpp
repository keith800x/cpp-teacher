#include "Analyzer.h"

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>

#include <nlohmann/json.hpp>

#include <sys/wait.h>
#include <unistd.h>

using json = nlohmann::json;

namespace
{
std::string readEntireFile(const std::filesystem::path& path)
{
    std::ifstream file(path);

    if (!file)
    {
        return {};
    }

    std::ostringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

std::string shellQuote(const std::string& value)
{
    std::string result = "'";

    for (char c : value)
    {
        if (c == '\'')
        {
            result += "'\\''";
        }
        else
        {
            result += c;
        }
    }

    result += "'";
    return result;
}

bool containsConstQualifier(const std::string& qualType)
{
    return qualType.find("const ") != std::string::npos ||
           qualType.find(" const") != std::string::npos;
}

bool isLvalueReference(const std::string& qualType)
{
    return qualType.find('&') != std::string::npos &&
           qualType.find("&&") == std::string::npos;
}

std::string astDumpFilterName(const Exercise& exercise)
{
    std::string requestedClass;
    bool needsLegacyMainFilter = false;

    for (const ConceptCheckSpec& check : exercise.getConceptChecks())
    {
        const bool classScopedCheck =
            check.type == "move_constructor" ||
            check.type == "copy_constructor" ||
            check.type == "virtual_destructor" ||
            (
                check.type == "std_move_initializer" &&
                !check.className.empty()
            );

        if (classScopedCheck)
        {
            if (check.className.empty())
            {
                return {};
            }

            if (requestedClass.empty())
            {
                requestedClass = check.className;
            }
            else if (requestedClass != check.className)
            {
                return {};
            }

            continue;
        }

        if (check.type == "std_move_initializer")
        {
            needsLegacyMainFilter = true;
        }
    }

    if (!requestedClass.empty() && !needsLegacyMainFilter)
    {
        return requestedClass;
    }

    if (requestedClass.empty() && needsLegacyMainFilter)
    {
        return "cpp_teacher_student_main";
    }

    return {};
}

const json* findNodeByKindAndName(
    const json& node,
    const std::string& kind,
    const std::string& name
)
{
    if (!node.is_object())
    {
        return nullptr;
    }

    if (node.value("kind", "") == kind &&
        node.value("name", "") == name)
    {
        return &node;
    }

    if (node.contains("inner") && node.at("inner").is_array())
    {
        for (const auto& child : node.at("inner"))
        {
            if (const json* found =
                    findNodeByKindAndName(child, kind, name))
            {
                return found;
            }
        }
    }

    return nullptr;
}

const json* findDirectParameter(
    const json& functionNode,
    const std::string& parameterName
)
{
    if (!functionNode.contains("inner") ||
        !functionNode.at("inner").is_array())
    {
        return nullptr;
    }

    for (const auto& child : functionNode.at("inner"))
    {
        if (child.is_object() &&
            child.value("kind", "") == "ParmVarDecl" &&
            child.value("name", "") == parameterName)
        {
            return &child;
        }
    }

    return nullptr;
}

std::string getQualifiedType(const json& declaration)
{
    if (!declaration.contains("type") ||
        !declaration.at("type").is_object())
    {
        return {};
    }

    return declaration.at("type").value("qualType", "");
}

bool subtreeReferencesVariable(
    const json& node,
    const std::string& variableName
)
{
    if (!node.is_object())
    {
        return false;
    }

    if (node.value("kind", "") == "DeclRefExpr" &&
        node.contains("referencedDecl") &&
        node.at("referencedDecl").is_object())
    {
        const json& declaration = node.at("referencedDecl");

        const std::string kind =
            declaration.value("kind", "");

        if ((kind == "VarDecl" || kind == "ParmVarDecl") &&
            declaration.value("name", "") == variableName)
        {
            return true;
        }
    }

    if (node.contains("inner") && node.at("inner").is_array())
    {
        for (const auto& child : node.at("inner"))
        {
            if (subtreeReferencesVariable(child, variableName))
            {
                return true;
            }
        }
    }

    return false;
}

bool subtreeReferencesFunctionName(
    const json& node,
    const std::string& functionName
)
{
    if (!node.is_object())
    {
        return false;
    }

    if (node.value("kind", "") == "DeclRefExpr")
    {
        if (node.contains("referencedDecl") &&
            node.at("referencedDecl").is_object() &&
            node.at("referencedDecl").value("name", "") ==
                functionName)
        {
            return true;
        }

        if (node.contains("foundReferencedDecl") &&
            node.at("foundReferencedDecl").is_object() &&
            node.at("foundReferencedDecl").value("name", "") ==
                functionName)
        {
            return true;
        }
    }

    if (node.contains("inner") && node.at("inner").is_array())
    {
        for (const auto& child : node.at("inner"))
        {
            if (subtreeReferencesFunctionName(child, functionName))
            {
                return true;
            }
        }
    }

    return false;
}

std::string sourceTextForRange(
    const json& node,
    const std::string& sourceCode
)
{
    if (!node.contains("range") ||
        !node.at("range").is_object())
    {
        return {};
    }

    const json& range = node.at("range");

    if (!range.contains("begin") ||
        !range.contains("end") ||
        !range.at("begin").is_object() ||
        !range.at("end").is_object())
    {
        return {};
    }

    const json& begin = range.at("begin");
    const json& end = range.at("end");

    if (!begin.contains("offset") ||
        !end.contains("offset"))
    {
        return {};
    }

    const std::size_t beginOffset =
        begin.at("offset").get<std::size_t>();

    const std::size_t endOffset =
        end.at("offset").get<std::size_t>();

    const std::size_t endTokenLength =
        end.value("tokLen", 1U);

    if (beginOffset >= sourceCode.size())
    {
        return {};
    }

    const std::size_t exclusiveEnd =
        std::min(
            sourceCode.size(),
            endOffset + endTokenLength
        );

    if (exclusiveEnd <= beginOffset)
    {
        return {};
    }

    return sourceCode.substr(
        beginOffset,
        exclusiveEnd - beginOffset
    );
}

std::string removeWhitespace(std::string value)
{
    value.erase(
        std::remove_if(
            value.begin(),
            value.end(),
            [](unsigned char c)
            {
                return std::isspace(c) != 0;
            }
        ),
        value.end()
    );

    return value;
}

bool callIsStdMoveWithArgument(
    const json& callNode,
    const std::string& sourceCode,
    const std::string& argumentName
)
{
    if (!callNode.is_object() ||
        callNode.value("kind", "") != "CallExpr" ||
        !callNode.contains("inner") ||
        !callNode.at("inner").is_array())
    {
        return false;
    }

    const auto& inner = callNode.at("inner");

    if (inner.size() < 2)
    {
        return false;
    }

    // The first child is the callee expression.
    const json& callee = inner.at(0);

    if (!subtreeReferencesFunctionName(callee, "move"))
    {
        return false;
    }

    const std::string calleeText =
        removeWhitespace(sourceTextForRange(callee, sourceCode));

    // The AST proves this is a real function call named move.
    // The source range proves the qualified spelling was std::move.
    if (calleeText.find("std::move") == std::string::npos &&
        calleeText.find("::std::move") == std::string::npos)
    {
        return false;
    }

    // Match the requested argument expression by source text first. This
    // supports bare variables and member expressions such as other.load_.
    const std::string expectedArgument =
        removeWhitespace(argumentName);

    const std::string actualArgument =
        removeWhitespace(
            sourceTextForRange(
                inner.at(1),
                sourceCode
            )
        );

    if (!actualArgument.empty() &&
        actualArgument == expectedArgument)
    {
        return true;
    }

    // Backward-compatible fallback for older bare VarDecl/ParmVarDecl checks.
    return subtreeReferencesVariable(
        inner.at(1),
        argumentName
    );
}

bool subtreeContainsStdMoveCall(
    const json& node,
    const std::string& sourceCode,
    const std::string& argumentName
)
{
    if (!node.is_object())
    {
        return false;
    }

    if (callIsStdMoveWithArgument(
            node,
            sourceCode,
            argumentName))
    {
        return true;
    }

    if (node.contains("inner") && node.at("inner").is_array())
    {
        for (const auto& child : node.at("inner"))
        {
            if (subtreeContainsStdMoveCall(
                    child,
                    sourceCode,
                    argumentName))
            {
                return true;
            }
        }
    }

    return false;
}


const json* findMemberInitializerContainingStdMove(
    const json& classNode,
    const std::string& memberName,
    const std::string& sourceCode,
    const std::string& argumentName
)
{
    if (!classNode.contains("inner") ||
        !classNode.at("inner").is_array())
    {
        return nullptr;
    }

    for (const auto& classChild : classNode.at("inner"))
    {
        if (!classChild.is_object() ||
            classChild.value("kind", "") != "CXXConstructorDecl" ||
            classChild.value("isImplicit", false) ||
            !classChild.contains("inner") ||
            !classChild.at("inner").is_array())
        {
            continue;
        }

        for (const auto& constructorChild : classChild.at("inner"))
        {
            if (!constructorChild.is_object() ||
                constructorChild.value("kind", "") !=
                    "CXXCtorInitializer" ||
                !constructorChild.contains("anyInit") ||
                !constructorChild.at("anyInit").is_object() ||
                constructorChild.at("anyInit").value("name", "") !=
                    memberName)
            {
                continue;
            }

            if (subtreeContainsStdMoveCall(
                    constructorChild,
                    sourceCode,
                    argumentName))
            {
                return &constructorChild;
            }
        }
    }

    return nullptr;
}


const json* findClassDefinition(
    const json& node,
    const std::string& className
)
{
    if (!node.is_object())
    {
        return nullptr;
    }

    if (node.value("kind", "") == "CXXRecordDecl" &&
        node.value("name", "") == className &&
        node.value("completeDefinition", false))
    {
        return &node;
    }

    if (node.contains("inner") && node.at("inner").is_array())
    {
        for (const auto& child : node.at("inner"))
        {
            if (const json* found =
                    findClassDefinition(child, className))
            {
                return found;
            }
        }
    }

    return nullptr;
}

const json* findDirectDestructor(
    const json& classNode,
    const std::string& className
)
{
    if (!classNode.contains("inner") ||
        !classNode.at("inner").is_array())
    {
        return nullptr;
    }

    const std::string destructorName =
        "~" + className;

    for (const auto& child : classNode.at("inner"))
    {
        if (child.is_object() &&
            child.value("kind", "") == "CXXDestructorDecl" &&
            child.value("name", "") == destructorName)
        {
            return &child;
        }
    }

    return nullptr;
}


const json* findUserDeclaredConstructorWithParameterType(
    const json& classNode,
    const std::string& className,
    const std::string& requiredParameterType,
    bool requireNoexcept
)
{
    if (!classNode.contains("inner") ||
        !classNode.at("inner").is_array())
    {
        return nullptr;
    }

    for (const auto& child : classNode.at("inner"))
    {
        if (!child.is_object() ||
            child.value("kind", "") != "CXXConstructorDecl" ||
            child.value("name", "") != className ||
            child.value("isImplicit", false))
        {
            continue;
        }

        if (!child.contains("inner") ||
            !child.at("inner").is_array())
        {
            continue;
        }

        const json* parameter = nullptr;

        for (const auto& constructorChild : child.at("inner"))
        {
            if (constructorChild.is_object() &&
                constructorChild.value("kind", "") == "ParmVarDecl")
            {
                // Copy/move constructors have exactly one object parameter
                // for the cases this lesson supports.
                if (parameter != nullptr)
                {
                    parameter = nullptr;
                    break;
                }

                parameter = &constructorChild;
            }
        }

        if (!parameter)
        {
            continue;
        }

        const std::string parameterType =
            getQualifiedType(*parameter);

        if (parameterType != requiredParameterType)
        {
            continue;
        }

        if (requireNoexcept)
        {
            const std::string constructorType =
                getQualifiedType(child);

            if (constructorType.find("noexcept") ==
                std::string::npos)
            {
                continue;
            }
        }

        return &child;
    }

    return nullptr;
}

ConceptCheckResult evaluateCheck(
    const ConceptCheckSpec& spec,
    const json& ast,
    const std::string& sourceCode
)
{
    ConceptCheckResult result;
    result.spec = spec;

    if (spec.type == "non_const_reference_parameter" ||
        spec.type == "const_reference_parameter")
    {
        const json* functionNode =
            findNodeByKindAndName(
                ast,
                "FunctionDecl",
                spec.functionName
            );

        if (!functionNode)
        {
            result.detail =
                "Function '" + spec.functionName + "' was not found.";
            return result;
        }

        const json* parameterNode =
            findDirectParameter(
                *functionNode,
                spec.parameterName
            );

        if (!parameterNode)
        {
            result.detail =
                "Parameter '" + spec.parameterName +
                "' was not found in function '" +
                spec.functionName + "'.";
            return result;
        }

        const std::string qualType =
            getQualifiedType(*parameterNode);

        if (qualType.empty())
        {
            result.detail =
                "Clang did not report a type for parameter '" +
                spec.parameterName + "'.";
            return result;
        }

        if (spec.type == "non_const_reference_parameter")
        {
            result.passed =
                isLvalueReference(qualType) &&
                !containsConstQualifier(qualType);

            result.detail =
                "Parameter type is '" + qualType + "'" +
                (result.passed
                    ? ": non-const lvalue reference detected."
                    : ", but a non-const lvalue reference is required.");

            return result;
        }

        result.passed =
            isLvalueReference(qualType) &&
            containsConstQualifier(qualType);

        result.detail =
            "Parameter type is '" + qualType + "'" +
            (result.passed
                ? ": const lvalue reference detected."
                : ", but a const lvalue reference is required.");

        return result;
    }

    if (spec.type == "non_const_reference_variable" ||
        spec.type == "const_reference_variable")
    {
        const json* variableNode =
            findNodeByKindAndName(
                ast,
                "VarDecl",
                spec.variableName
            );

        if (!variableNode)
        {
            result.detail =
                "Variable '" + spec.variableName +
                "' was not found.";
            return result;
        }

        const std::string qualType =
            getQualifiedType(*variableNode);

        const bool referenceType =
            isLvalueReference(qualType);

        const bool constType =
            containsConstQualifier(qualType);

        const bool targetsRequestedVariable =
            subtreeReferencesVariable(
                *variableNode,
                spec.argumentName
            );

        if (spec.type ==
            "non_const_reference_variable")
        {
            result.passed =
                referenceType &&
                !constType &&
                targetsRequestedVariable;

            result.detail =
                "Variable '" + spec.variableName +
                "' has type '" + qualType + "'" +
                (result.passed
                    ? " and aliases '" +
                        spec.argumentName + "'."
                    : ", but a non-const lvalue reference alias to '" +
                        spec.argumentName + "' is required.");

            return result;
        }

        result.passed =
            referenceType &&
            constType &&
            targetsRequestedVariable;

        result.detail =
            "Variable '" + spec.variableName +
            "' has type '" + qualType + "'" +
            (result.passed
                ? " and provides a const alias to '" +
                    spec.argumentName + "'."
                : ", but a const lvalue reference alias to '" +
                    spec.argumentName + "' is required.");

        return result;
    }

    if (spec.type == "std_move_initializer")
    {
        if (!spec.className.empty())
        {
            const json* classNode =
                findClassDefinition(
                    ast,
                    spec.className
                );

            if (!classNode)
            {
                result.detail =
                    "Class '" + spec.className +
                    "' was not found while checking member initializer '" +
                    spec.variableName + "'.";
                return result;
            }

            const json* initializerNode =
                findMemberInitializerContainingStdMove(
                    *classNode,
                    spec.variableName,
                    sourceCode,
                    spec.argumentName
                );

            result.passed =
                (initializerNode != nullptr);

            if (result.passed)
            {
                result.detail =
                    "Member initializer for '" +
                    spec.className + "::" +
                    spec.variableName +
                    "' contains a real std::move(" +
                    spec.argumentName + ") call.";
            }
            else
            {
                result.detail =
                    "No member initializer for '" +
                    spec.className + "::" +
                    spec.variableName +
                    "' contains std::move(" +
                    spec.argumentName + ").";
            }

            return result;
        }

        const json* variableNode =
            findNodeByKindAndName(
                ast,
                "VarDecl",
                spec.variableName
            );

        if (!variableNode)
        {
            result.detail =
                "Variable '" + spec.variableName +
                "' was not found.";
            return result;
        }

        result.passed =
            subtreeContainsStdMoveCall(
                *variableNode,
                sourceCode,
                spec.argumentName
            );

        if (result.passed)
        {
            result.detail =
                "Initializer for '" + spec.variableName +
                "' contains a real std::move(" +
                spec.argumentName + ") call.";
        }
        else
        {
            result.detail =
                "Initializer for '" + spec.variableName +
                "' does not contain std::move(" +
                spec.argumentName + ").";
        }

        return result;
    }

    if (spec.type == "virtual_destructor")
    {
        const json* classNode =
            findClassDefinition(
                ast,
                spec.className
            );

        if (!classNode)
        {
            result.detail =
                "Class '" + spec.className +
                "' was not found.";
            return result;
        }

        const json* destructorNode =
            findDirectDestructor(
                *classNode,
                spec.className
            );

        if (!destructorNode)
        {
            result.detail =
                "Clang did not report a destructor for class '" +
                spec.className + "'.";
            return result;
        }

        result.passed =
            destructorNode->value("virtual", false);

        if (result.passed)
        {
            result.detail =
                "Destructor '~" + spec.className +
                "()' is virtual.";
        }
        else
        {
            const bool implicit =
                destructorNode->value("isImplicit", false);

            if (implicit)
            {
                result.detail =
                    "Class '" + spec.className +
                    "' has only an implicit non-virtual destructor.";
            }
            else
            {
                result.detail =
                    "Destructor '~" + spec.className +
                    "()' exists but is not virtual.";
            }
        }

        return result;
    }

    if (spec.type == "copy_constructor" ||
        spec.type == "move_constructor")
    {
        const json* classNode =
            findClassDefinition(
                ast,
                spec.className
            );

        if (!classNode)
        {
            result.detail =
                "Class '" + spec.className +
                "' was not found.";
            return result;
        }

        if (spec.type == "copy_constructor")
        {
            const std::string requiredType =
                "const " + spec.className + " &";

            const json* constructorNode =
                findUserDeclaredConstructorWithParameterType(
                    *classNode,
                    spec.className,
                    requiredType,
                    false
                );

            result.passed =
                (constructorNode != nullptr);

            if (result.passed)
            {
                result.detail =
                    "User-declared copy constructor '" +
                    spec.className +
                    "(const " + spec.className +
                    "&)' detected.";
            }
            else
            {
                result.detail =
                    "No user-declared copy constructor '" +
                    spec.className +
                    "(const " + spec.className +
                    "&)' was found.";
            }

            return result;
        }

        const std::string requiredType =
            spec.className + " &&";

        const json* constructorNode =
            findUserDeclaredConstructorWithParameterType(
                *classNode,
                spec.className,
                requiredType,
                false
            );

        result.passed =
            (constructorNode != nullptr);

        if (result.passed)
        {
            result.detail =
                "User-declared move constructor '" +
                spec.className +
                "(" + spec.className +
                "&&)' detected.";
        }
        else
        {
            result.detail =
                "No user-declared move constructor '" +
                spec.className +
                "(" + spec.className +
                "&&)' was found.";
        }

        return result;
    }

    result.detail =
        "Unknown concept check type: " + spec.type;

    return result;
}
}

ClangAstAnalyzer::ClangAstAnalyzer(std::string compiler)
    : compiler_(std::move(compiler))
{
}

AnalysisResult ClangAstAnalyzer::analyze(
    const Exercise& exercise,
    const std::string& sourceCode
) const
{
    namespace fs = std::filesystem;

    AnalysisResult result;

    if (exercise.getConceptChecks().empty())
    {
        result.analysisSucceeded = true;
        return result;
    }

    const fs::path baseDirectory =
        fs::temp_directory_path() /
        ("cpp_teacher_ast_" + std::to_string(::getpid()));

    fs::create_directories(baseDirectory);

    const fs::path sourcePath = baseDirectory / "student.cpp";
    const fs::path astPath = baseDirectory / "ast.json";
    const fs::path diagnosticsPath =
        baseDirectory / "ast_diagnostics.txt";

    {
        std::ofstream file(sourcePath);

        if (!file)
        {
            throw std::runtime_error(
                "Could not create AST analysis source file."
            );
        }

        file << sourceCode;
    }

    std::string command =
        shellQuote(compiler_) +
        " -std=c++20 -fsyntax-only ";

    const std::string filterName =
        astDumpFilterName(exercise);

    if (!filterName.empty())
    {
        // Standard-library headers can make a full JSON AST hundreds of MB.
        // Prefer the learner class for constructor/member checks. Preserve
        // renamed-main filtering only for legacy local std::move checks.
        if (filterName == "cpp_teacher_student_main")
        {
            command +=
                "-Dmain=cpp_teacher_student_main ";
        }

        command +=
            "-Xclang -ast-dump=json "
            "-Xclang -ast-dump-filter "
            "-Xclang " +
            shellQuote(filterName) +
            " ";
    }
    else
    {
        command += "-Xclang -ast-dump=json ";
    }

    command +=
        shellQuote(sourcePath.string()) +
        " > " +
        shellQuote(astPath.string()) +
        " 2> " +
        shellQuote(diagnosticsPath.string());

    const int rawStatus = std::system(command.c_str());

    result.diagnostics =
        readEntireFile(diagnosticsPath);

    if (rawStatus == -1 ||
        !WIFEXITED(rawStatus) ||
        WEXITSTATUS(rawStatus) != 0)
    {
        result.analysisSucceeded = false;

        if (result.diagnostics.empty())
        {
            result.diagnostics =
                "Clang AST analysis failed.";
        }

        std::error_code ignored;
        fs::remove_all(baseDirectory, ignored);
        return result;
    }

    try
    {
        std::ifstream astFile(astPath);

        if (!astFile)
        {
            throw std::runtime_error(
                "Could not open generated AST JSON."
            );
        }

        std::ostringstream astBuffer;
        astBuffer << astFile.rdbuf();

        std::string astText = astBuffer.str();

        // Older Clang versions may prepend a line such as:
        // "Dumping cpp_teacher_student_main:"
        // before filtered JSON output. Find the first JSON object
        // so both older and newer Clang versions are supported.
        const std::size_t jsonStart = astText.find('{');

        if (jsonStart == std::string::npos)
        {
            throw std::runtime_error(
                "Clang AST output did not contain a JSON object."
            );
        }

        astText.erase(0, jsonStart);

        json ast = json::parse(astText);

        for (const ConceptCheckSpec& spec :
             exercise.getConceptChecks())
        {
            result.checks.push_back(
                evaluateCheck(
                    spec,
                    ast,
                    sourceCode
                )
            );
        }

        result.analysisSucceeded = true;
    }
    catch (const std::exception& error)
    {
        result.analysisSucceeded = false;
        result.diagnostics +=
            std::string("\nCould not parse Clang AST JSON: ") +
            error.what() + "\n";
    }

    std::error_code ignored;
    fs::remove_all(baseDirectory, ignored);

    return result;
}
