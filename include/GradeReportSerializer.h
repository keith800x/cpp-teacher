#pragma once

#include "Exercise.h"
#include "Grader.h"

#include <string>

class GradeReportSerializer
{
public:
    std::string toJsonString(
        const Exercise& exercise,
        const GradeResult& result
    ) const;
};
