cmake_minimum_required(VERSION 3.16)

project(CppTeacherStep28 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)

FetchContent_Declare(
    nlohmann_json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
)

FetchContent_MakeAvailable(nlohmann_json)

add_executable(cpp_teacher
    src/main.cpp
    src/Exercise.cpp
    src/Compiler.cpp
    src/Runner.cpp
    src/Analyzer.cpp
    src/Grader.cpp
    src/GradeReportSerializer.cpp
    src/Trace.cpp
    src/TraceBuilder.cpp
    src/RuntimeTraceParser.cpp
    src/MemoryStateBuilder.cpp
    src/MemoryStatePrinter.cpp
    src/MemoryTimelineSerializer.cpp
    src/TimelineManifestWriter.cpp
)

target_include_directories(cpp_teacher PRIVATE include)
target_link_libraries(cpp_teacher PRIVATE nlohmann_json::nlohmann_json)
