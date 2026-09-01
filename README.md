# C++ Teacher — Step 2

This step adds the first real piece of the exercise engine:

> Load an exercise from JSON and display it from a C++ program.

## Project structure

```text
cpp-teacher-step2/
├── CMakeLists.txt
├── README.md
├── exercises/
│   └── unique_ptr_001.json
├── examples/
│   ├── broken.cpp
│   └── solution.cpp
└── src/
    └── main.cpp
```

## What you are learning in this step

The application now separates **exercise content** from **program logic**.

Instead of hard-coding this:

```cpp
std::cout << "Transfer Ownership";
```

the program reads:

```text
exercises/unique_ptr_001.json
```

That same pattern will later allow:

- many exercises,
- AI-generated exercises,
- difficulty levels,
- hints,
- solutions,
- visualization metadata.

## Prerequisites

Install:

- CMake 3.20+
- a C++20 compiler
- Git

Examples:

- Windows: Visual Studio 2022 with Desktop development with C++
- macOS: Xcode command-line tools
- Linux: GCC or Clang

The first CMake configure downloads `nlohmann/json` from GitHub.

## Build

Open a terminal in this folder.

### Windows — Visual Studio generator

```powershell
cmake -S . -B build
cmake --build build --config Debug
.\build\Debug\cpp_teacher.exe
```

### macOS / Linux

```bash
cmake -S . -B build
cmake --build build
./build/cpp_teacher
```

## Expected output

You should see something similar to:

```text
========================================
          C++ TEACHER - EXERCISE
========================================

Title:      Transfer Ownership
Topic:      unique_ptr
Difficulty: 1

Learning objective:
Understand that std::unique_ptr ownership is transferred rather than copied.

Instructions:
Fix the code so ownership of the Player object is transferred from player to second.

Starter code:
----------------------------------------
#include <memory>

struct Player
{
};

int main()
{
    auto player = std::make_unique<Player>();
    auto second = player;

    return 0;
}
----------------------------------------

Hints:
  1. A std::unique_ptr cannot be copied.
  2. Ownership needs to move from player to second.
  3. Use std::move to transfer ownership.

Exercise loaded successfully.
```

## Test the C++ exercise itself

The `examples` folder contains both versions.

Broken version:

```bash
clang++ -std=c++20 examples/broken.cpp -o broken
```

This should fail because `std::unique_ptr` cannot be copied.

Correct version:

```bash
clang++ -std=c++20 examples/solution.cpp -o solution
```

This should compile successfully.

You can substitute `g++` for `clang++`.

## What the code is doing

The important part of `src/main.cpp` is:

```cpp
std::ifstream file(exercisePath);

json exercise;
file >> exercise;
```

This:

1. opens the JSON file,
2. parses it,
3. stores the result in `exercise`.

Then:

```cpp
exercise.at("title").get<std::string>()
```

reads a field from the exercise.

And:

```cpp
const auto& hints = exercise.at("hints");

for (std::size_t i = 0; i < hints.size(); ++i)
{
    std::cout << hints.at(i).get<std::string>();
}
```

reads the array of hints.

## Why this matters

You now have the beginning of this architecture:

```text
Exercise JSON
     |
     v
Exercise Loader
     |
     v
C++ Teacher
```

Later it becomes:

```text
OpenAI API
     |
     v
Exercise JSON
     |
     v
Validation
     |
     v
Exercise Loader
     |
     +------> Editor
     |
     +------> Compiler
     |
     +------> Visualizer
```

## Your goal before moving on

Do not add anything else until:

1. CMake configures successfully.
2. The project compiles.
3. `cpp_teacher` runs.
4. The exercise information appears in your terminal.
5. You understand where `main.cpp` gets each displayed value from.

Once that works, Step 3 should be:

> Turn the loader into an `Exercise` C++ class instead of passing raw JSON around.

That will give the project its first proper application architecture.
