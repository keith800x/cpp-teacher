const state = {
    document: null,
    index: 0,
    playTimer: null,

    library: [],
    activeView: "library",

    activeExerciseMetadata: null,
    activeExerciseDocument: null,
    activeExerciseProgress: null,

    latestGradeTimeline: null,
    currentVisualizationKind: null,

    revealedHintCount: 0,
};

const elements = {
    libraryView: document.querySelector("#libraryView"),
    authoringView: document.querySelector("#authoringView"),
    exerciseView: document.querySelector("#exerciseView"),
    visualizerView: document.querySelector("#visualizerView"),

    availableCount: document.querySelector("#availableCount"),
    solvedCount: document.querySelector("#solvedCount"),
    attemptedCount: document.querySelector("#attemptedCount"),

    exerciseSearch: document.querySelector("#exerciseSearch"),
    topicFilter: document.querySelector("#topicFilter"),
    difficultyFilter: document.querySelector("#difficultyFilter"),
    statusFilter: document.querySelector("#statusFilter"),
    clearFiltersButton: document.querySelector("#clearFiltersButton"),

    libraryResultCount: document.querySelector("#libraryResultCount"),
    libraryFilterSummary: document.querySelector("#libraryFilterSummary"),
    exerciseCards: document.querySelector("#exerciseCards"),

    backToLibraryButton: document.querySelector("#backToLibraryButton"),

    exerciseTopicBadge: document.querySelector("#exerciseTopicBadge"),
    exerciseDifficultyBadge: document.querySelector("#exerciseDifficultyBadge"),
    exerciseTitle: document.querySelector("#exerciseTitle"),
    exerciseObjective: document.querySelector("#exerciseObjective"),
    exerciseScenario: document.querySelector("#exerciseScenario"),
    exerciseProblem: document.querySelector("#exerciseProblem"),
    exerciseInstructions: document.querySelector("#exerciseInstructions"),

    exerciseHints: document.querySelector("#exerciseHints"),
    revealHintButton: document.querySelector("#revealHintButton"),
    hintStatus: document.querySelector("#hintStatus"),

    codeEditor: document.querySelector("#codeEditor"),
    editorStatus: document.querySelector("#editorStatus"),
    resetStarterButton: document.querySelector("#resetStarterButton"),
    runGradeButton: document.querySelector("#runGradeButton"),

    gradeSummary: document.querySelector("#gradeSummary"),
    gradeStages: document.querySelector("#gradeStages"),
    gradeOutput: document.querySelector("#gradeOutput"),
    lineNumbers: document.querySelector("#lineNumbers"),

    openLatestVisualizationButton:
        document.querySelector("#openLatestVisualizationButton"),

    solutionPanel: document.querySelector("#solutionPanel"),
    solutionLockBadge: document.querySelector("#solutionLockBadge"),
    solutionMessage: document.querySelector("#solutionMessage"),
    viewSolutionButton: document.querySelector("#viewSolutionButton"),
    solutionContent: document.querySelector("#solutionContent"),
    solutionCode: document.querySelector("#solutionCode"),
    solutionExplanation: document.querySelector("#solutionExplanation"),
    visualizeSolutionButton: document.querySelector("#visualizeSolutionButton"),

    backToExerciseButton: document.querySelector("#backToExerciseButton"),
    visualizationExerciseTitle:
        document.querySelector("#visualizationExerciseTitle"),

    statusPanel: document.querySelector("#statusPanel"),
    visualizerApp: document.querySelector("#visualizerApp"),

    exerciseId: document.querySelector("#exerciseId"),
    schemaVersion: document.querySelector("#schemaVersion"),

    currentStep: document.querySelector("#currentStep"),
    totalSteps: document.querySelector("#totalSteps"),

    eventType: document.querySelector("#eventType"),
    eventSubject: document.querySelector("#eventSubject"),
    eventDetail: document.querySelector("#eventDetail"),

    activeScopes: document.querySelector("#activeScopes"),
    stackValues: document.querySelector("#stackValues"),
    stackAliases: document.querySelector("#stackAliases"),
    stackObjects: document.querySelector("#stackObjects"),
    heapResources: document.querySelector("#heapResources"),

    previousButton: document.querySelector("#previousButton"),
    playButton: document.querySelector("#playButton"),
    nextButton: document.querySelector("#nextButton"),
    timelineSlider: document.querySelector("#timelineSlider"),

    memoryStage: document.querySelector("#memoryStage"),
    arrowLayer: document.querySelector("#arrowLayer"),

    teachingTitle: document.querySelector("#teachingTitle"),
    teachingText: document.querySelector("#teachingText"),
};

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function setActiveView(viewName) {
    state.activeView = viewName;

    elements.libraryView.classList.toggle(
        "hidden",
        viewName !== "library"
    );

    elements.authoringView.classList.toggle(
        "hidden",
        viewName !== "authoring"
    );

    elements.exerciseView.classList.toggle(
        "hidden",
        viewName !== "exercise"
    );

    elements.visualizerView.classList.toggle(
        "hidden",
        viewName !== "visualizer"
    );

    if (
        viewName === "visualizer" &&
        state.document
    ) {
        requestAnimationFrame(
            drawPointerArrows
        );
    }

    window.scrollTo({
        top: 0,
        behavior: "instant",
    });
}

function topicLabel(value) {
    const known = {
        references: "References",
        raii_scope: "RAII and Scope",
        move_semantics: "Move Semantics",
    };

    if (known[value]) {
        return known[value];
    }

    return String(value)
        .split("_")
        .map(
            (part) =>
                part.length > 0
                    ? (
                        part[0].toUpperCase() +
                        part.slice(1)
                      )
                    : part
        )
        .join(" ");
}

function difficultyLabel(value) {
    if (value === "easy") {
        return "Easy";
    }

    if (value === "hard") {
        return "Hard";
    }

    return "Medium";
}

function statusLabel(value) {
    if (value === "solved") {
        return "Solved";
    }

    if (value === "attempted") {
        return "Attempted";
    }

    return "Unsolved";
}

function exerciseStatus(exercise) {
    return (
        exercise.progress?.status ??
        "unsolved"
    );
}

function exerciseById(exerciseId) {
    return (
        state.library.find(
            (exercise) =>
                exercise.id === exerciseId
        ) ?? null
    );
}

async function fetchExerciseLibrary() {
    const response =
        await fetch(
            "/api/exercises",
            {
                cache: "no-store",
            }
        );

    const payload =
        await response.json();

    if (
        !response.ok ||
        !payload.ok ||
        !Array.isArray(payload.exercises)
    ) {
        throw new Error(
            payload.error ??
            "Exercise library response is malformed."
        );
    }

    return payload.exercises;
}

async function loadExerciseLibrary() {
    elements.exerciseCards.innerHTML =
        `<div class="status-panel">
            Loading exercises…
         </div>`;

    try {
        state.library =
            await fetchExerciseLibrary();

        populateTopicFilter();
        renderExerciseLibrary();
    } catch (error) {
        elements.exerciseCards.innerHTML =
            `<div class="status-panel error">
                <strong>Could not load exercises.</strong>
                <span>${escapeHtml(error.message)}</span>
             </div>`;
    }
}

async function refreshLibraryData() {
    try {
        state.library =
            await fetchExerciseLibrary();

        populateTopicFilter();
        renderExerciseLibrary();

        if (state.activeExerciseMetadata) {
            const refreshed =
                exerciseById(
                    state.activeExerciseMetadata.id
                );

            if (refreshed) {
                state.activeExerciseMetadata =
                    refreshed;
            }
        }
    } catch {
        // Keep the current exercise usable even if a library refresh fails.
    }
}

function populateTopicFilter() {
    const selected =
        elements.topicFilter.value;

    const topics =
        [...new Set(
            state.library.map(
                (exercise) =>
                    exercise.topic
            )
        )].sort(
            (left, right) =>
                left.localeCompare(right)
        );

    elements.topicFilter.innerHTML =
        `<option value="all">All topics</option>`;

    for (const topic of topics) {
        const option =
            document.createElement("option");

        option.value = topic;
        option.textContent =
            topicLabel(topic);

        elements.topicFilter.appendChild(
            option
        );
    }

    if (topics.includes(selected)) {
        elements.topicFilter.value =
            selected;
    }
}

function filteredExercises() {
    const search =
        elements.exerciseSearch.value
            .trim()
            .toLowerCase();

    const topic =
        elements.topicFilter.value;

    const difficulty =
        elements.difficultyFilter.value;

    const status =
        elements.statusFilter.value;

    return state.library.filter(
        (exercise) => {
            const currentStatus =
                exerciseStatus(exercise);

            const searchable = [
                exercise.title,
                exercise.topic,
                exercise.learner_goal,
                exercise.scenario,
                exercise.problem_statement,
            ]
                .join(" ")
                .toLowerCase();

            return (
                (
                    !search ||
                    searchable.includes(search)
                ) &&
                (
                    topic === "all" ||
                    exercise.topic === topic
                ) &&
                (
                    difficulty === "all" ||
                    exercise.difficulty === difficulty
                ) &&
                (
                    status === "all" ||
                    currentStatus === status
                )
            );
        }
    );
}

function renderExerciseLibrary() {
    const exercises =
        filteredExercises();

    const solved =
        state.library.filter(
            (exercise) =>
                exerciseStatus(exercise) ===
                "solved"
        ).length;

    const attempted =
        state.library.filter(
            (exercise) =>
                exerciseStatus(exercise) ===
                "attempted"
        ).length;

    elements.availableCount.textContent =
        String(state.library.length);

    elements.solvedCount.textContent =
        String(solved);

    elements.attemptedCount.textContent =
        String(attempted);

    elements.libraryResultCount.textContent =
        `${exercises.length} exercise${
            exercises.length === 1
                ? ""
                : "s"
        }`;

    const activeFilters = [];

    if (
        elements.topicFilter.value !==
        "all"
    ) {
        activeFilters.push(
            topicLabel(
                elements.topicFilter.value
            )
        );
    }

    if (
        elements.difficultyFilter.value !==
        "all"
    ) {
        activeFilters.push(
            difficultyLabel(
                elements.difficultyFilter.value
            )
        );
    }

    if (
        elements.statusFilter.value !==
        "all"
    ) {
        activeFilters.push(
            statusLabel(
                elements.statusFilter.value
            )
        );
    }

    if (
        elements.exerciseSearch.value.trim()
    ) {
        activeFilters.push(
            `Search: "${elements.exerciseSearch.value.trim()}"`
        );
    }

    elements.libraryFilterSummary.textContent =
        activeFilters.length > 0
            ? activeFilters.join(" · ")
            : "Showing all exercises";

    elements.exerciseCards.innerHTML = "";

    if (exercises.length === 0) {
        elements.exerciseCards.innerHTML =
            `<div class="library-empty-state">
                No exercises match these filters.
             </div>`;

        return;
    }

    for (const exercise of exercises) {
        const status =
            exerciseStatus(exercise);

        const card =
            document.createElement("article");

        card.className =
            "exercise-library-card";

        const solveLabel =
            status === "solved"
                ? "Review exercise"
                : (
                    status === "attempted"
                        ? "Continue exercise"
                        : "Solve exercise"
                  );

        const attemptText =
            exercise.progress?.attempt_count > 0
                ? (
                    `${exercise.progress.attempt_count} attempt${
                        exercise.progress.attempt_count === 1
                            ? ""
                            : "s"
                    } saved`
                  )
                : "No attempts yet";

        card.innerHTML = `
            <div class="library-card-topline">
                <span class="topic-badge">
                    ${escapeHtml(
                        topicLabel(
                            exercise.topic
                        )
                    )}
                </span>

                <span class="difficulty-badge ${escapeHtml(exercise.difficulty)}">
                    ${escapeHtml(
                        difficultyLabel(
                            exercise.difficulty
                        )
                    )}
                </span>

                <span class="exercise-status-badge ${escapeHtml(status)}">
                    ${escapeHtml(
                        statusLabel(status)
                    )}
                </span>
            </div>

            <div>
                <h3>
                    ${escapeHtml(exercise.title)}
                </h3>

                <p class="library-card-objective">
                    ${escapeHtml(
                        exercise.learner_goal
                    )}
                </p>
            </div>

            <div class="library-attempt-summary">
                ${escapeHtml(attemptText)}
            </div>

            <div class="library-card-actions">
                <button
                    class="primary-button"
                    type="button"
                    data-open-exercise="${escapeHtml(exercise.id)}"
                >
                    ${solveLabel}
                </button>
            </div>
        `;

        elements.exerciseCards.appendChild(
            card
        );
    }
}

function exerciseUrl(exerciseId) {
    return (
        `/api/exercises/${encodeURIComponent(exerciseId)}`
    );
}

function latestAttemptVisualizationUrl(
    exerciseId
) {
    return (
        `/api/exercises/${encodeURIComponent(exerciseId)}` +
        "/attempts/latest/visualization"
    );
}

function solutionRevealUrl(
    exerciseId
) {
    return (
        `/api/exercises/${encodeURIComponent(exerciseId)}` +
        "/solution/reveal"
    );
}

function solutionVisualizationUrl(
    exerciseId
) {
    return (
        `/api/exercises/${encodeURIComponent(exerciseId)}` +
        "/solution/visualize"
    );
}

function gradeStatusLabel(status) {
    if (status === "pass") {
        return "Pass";
    }

    if (status === "fail") {
        return "Fail";
    }

    if (status === "blocked") {
        return "Blocked";
    }

    return "Skipped";
}

function stageCard(
    title,
    stage,
    bodyHtml
) {
    const status =
        stage?.status ?? "skipped";

    return `
        <article class="grade-stage ${escapeHtml(status)}">
            <div class="grade-stage-header">
                <span class="grade-stage-title">
                    ${escapeHtml(title)}
                </span>

                <span class="grade-status-badge ${escapeHtml(status)}">
                    ${escapeHtml(
                        gradeStatusLabel(status)
                    )}
                </span>
            </div>

            ${bodyHtml}
        </article>
    `;
}

function renderGradeStages(
    grade,
    hasTimeline
) {
    if (!grade) {
        elements.gradeStages.innerHTML =
            `<div class="grade-empty-state">
                No structured grade report returned.
            </div>`;

        return;
    }

    const compilation =
        grade.compilation ?? {};

    const semantic =
        grade.semantic_checks ?? {};

    const hidden =
        grade.hidden_tests ?? {};

    const runtime =
        grade.runtime ?? {};

    const output =
        grade.output_check ?? {};

    const requirements =
        grade.legacy_requirements ?? {};

    const semanticChecks =
        (semantic.checks ?? [])
            .map(
                (check) => `
                    <li class="semantic-check">
                        <strong>
                            ${check.passed ? "✓" : "✕"}
                            ${escapeHtml(
                                check.type ??
                                "semantic check"
                            )}
                        </strong>
                        <br>
                        ${escapeHtml(
                            check.detail ?? ""
                        )}
                    </li>
                `
            )
            .join("");

    const warnings =
        (runtime.trace_warnings ?? [])
            .map(
                (warning) => `
                    <li class="semantic-check">
                        <strong>
                            ${escapeHtml(
                                warning.subject ??
                                "runtime"
                            )}
                        </strong>
                        <br>
                        ${escapeHtml(
                            warning.detail ?? ""
                        )}
                    </li>
                `
            )
            .join("");

    const compilationBody =
        compilation.diagnostics
            ? (
                `<pre class="diagnostic-box">` +
                `${escapeHtml(compilation.diagnostics)}` +
                `</pre>`
              )
            : (
                `<div class="grade-stage-detail">` +
                `clang++ accepted the submitted source.` +
                `</div>`
              );

    const semanticBody =
        semantic.used
            ? (
                semanticChecks
                    ? (
                        `<ul class="semantic-check-list">` +
                        `${semanticChecks}` +
                        `</ul>`
                      )
                    : (
                        `<div class="grade-stage-detail">` +
                        `No semantic check details were produced.` +
                        `</div>`
                      )
              )
            : (
                `<div class="grade-stage-detail">` +
                `This exercise has no Clang AST semantic checks.` +
                `</div>`
              );

    const hiddenBody =
        hidden.used
            ? (
                `<div class="grade-stage-detail">` +
                `Hidden test harness ` +
                `${hidden.passed ? "passed." : "did not pass."}` +
                `</div>`
              )
            : (
                `<div class="grade-stage-detail">` +
                `No hidden tests for this exercise.` +
                `</div>`
              );

    const runtimeParts = [
        `started: ${Boolean(runtime.started)}`,
        `timeout: ${Boolean(runtime.timed_out)}`,
        `exit code: ${runtime.exit_code ?? "—"}`,
    ];

    let runtimeBody =
        `<div class="grade-stage-detail">
            ${runtimeParts.map(escapeHtml).join("<br>")}
         </div>`;

    if (warnings) {
        runtimeBody +=
            `<ul class="warning-list">
                ${warnings}
             </ul>`;
    }

    if (runtime.feedback) {
        runtimeBody +=
            `<pre class="diagnostic-box">
${escapeHtml(runtime.feedback)}
</pre>`;
    }

    const outputBody =
        output.used
            ? (
                `<div class="grade-stage-detail">` +
                `Expected-output comparison ` +
                `${output.passed ? "passed." : "failed."}` +
                `</div>`
              )
            : (
                `<div class="grade-stage-detail">` +
                `This exercise does not use exact stdout comparison.` +
                `</div>`
              );

    const visualizationStage = {
        status:
            hasTimeline
                ? "pass"
                : "skipped",
    };

    const visualizationBody =
        `<div class="grade-stage-detail">
            ${
                hasTimeline
                    ? "A visualization was generated from this submission."
                    : "No visualization was generated for this submission."
            }
         </div>`;

    let requirementsBody =
        `<div class="grade-stage-detail">
            No legacy source-fragment requirements.
         </div>`;

    if (requirements.used) {
        const missing =
            requirements.missing ?? [];

        requirementsBody =
            missing.length === 0
                ? (
                    `<div class="grade-stage-detail">` +
                    `Required source fragments are present.` +
                    `</div>`
                  )
                : (
                    `<div class="grade-stage-detail">` +
                    `Missing: ${escapeHtml(missing.join(", "))}` +
                    `</div>`
                  );
    }

    elements.gradeStages.innerHTML =
        stageCard(
            "Compilation",
            compilation,
            compilationBody
        ) +
        stageCard(
            "Semantic checks",
            semantic,
            semanticBody
        ) +
        stageCard(
            "Hidden tests",
            hidden,
            hiddenBody
        ) +
        stageCard(
            "Runtime",
            runtime,
            runtimeBody
        ) +
        stageCard(
            "Output check",
            output,
            outputBody
        ) +
        stageCard(
            "Source requirements",
            requirements,
            requirementsBody
        ) +
        stageCard(
            "Visualization",
            visualizationStage,
            visualizationBody
        );
}

function updateLineNumbers() {
    const editor =
        elements.codeEditor;

    const lineCount =
        Math.max(
            1,
            editor.value.split("\n").length
        );

    elements.lineNumbers.textContent =
        Array.from(
            {
                length: lineCount,
            },
            (_, index) =>
                String(index + 1)
        ).join("\n");

    elements.lineNumbers.scrollTop =
        editor.scrollTop;
}

function renderRevealedHints() {
    const hints =
        state.activeExerciseDocument?.hints ??
        [];

    elements.exerciseHints.innerHTML = "";

    for (
        let index = 0;
        index < state.revealedHintCount;
        ++index
    ) {
        const item =
            document.createElement("li");

        item.textContent =
            hints[index];

        elements.exerciseHints.appendChild(
            item
        );
    }

    const remaining =
        hints.length -
        state.revealedHintCount;

    elements.revealHintButton.disabled =
        (
            hints.length === 0 ||
            remaining <= 0
        );

    if (hints.length === 0) {
        elements.hintStatus.textContent =
            "This exercise has no hints.";
    }
    else if (
        state.revealedHintCount === 0
    ) {
        elements.hintStatus.textContent =
            "Hints are hidden until you request one.";
    }
    else if (remaining > 0) {
        elements.hintStatus.textContent =
            `${remaining} hint${
                remaining === 1
                    ? ""
                    : "s"
            } remaining.`;
    }
    else {
        elements.hintStatus.textContent =
            "All hints revealed.";
    }
}

function resetSolutionDisplay() {
    elements.solutionContent.classList.add(
        "hidden"
    );

    elements.solutionCode.textContent = "";
    elements.solutionExplanation.textContent = "";
}

function updateSolutionPanel(progress) {
    state.activeExerciseProgress =
        progress;

    resetSolutionDisplay();

    const available =
        Boolean(
            progress?.solution_available
        );

    const revealed =
        Boolean(
            progress?.solution_revealed
        );

    if (!available) {
        elements.solutionLockBadge.textContent =
            "Locked";

        elements.solutionLockBadge.className =
            "solution-lock-badge locked";

        elements.solutionMessage.textContent =
            "The reference solution unlocks after at least one failed attempt.";

        elements.viewSolutionButton.disabled =
            true;

        elements.viewSolutionButton.textContent =
            "View solution";

        return;
    }

    elements.solutionLockBadge.textContent =
        revealed
            ? "Unlocked"
            : "Available";

    elements.solutionLockBadge.className =
        "solution-lock-badge unlocked";

    elements.solutionMessage.textContent =
        revealed
            ? "You previously unlocked this solution. Reveal it again when you want to review it."
            : "You have made a failed attempt, so the reference solution is now available.";

    elements.viewSolutionButton.disabled =
        false;

    elements.viewSolutionButton.textContent =
        revealed
            ? "View solution again"
            : "View solution";
}

function renderExerciseDocument(
    metadata,
    exercise,
    progress,
    savedSubmission
) {
    state.activeExerciseMetadata =
        metadata;

    state.activeExerciseDocument =
        exercise;

    state.activeExerciseProgress =
        progress;

    state.latestGradeTimeline = null;
    state.currentVisualizationKind = null;
    state.revealedHintCount = 0;

    elements.exerciseTopicBadge.textContent =
        topicLabel(
            metadata.topic
        );

    elements.exerciseDifficultyBadge.textContent =
        difficultyLabel(
            metadata.difficulty
        );

    elements.exerciseDifficultyBadge.className =
        (
            "difficulty-badge " +
            metadata.difficulty
        );

    elements.exerciseTitle.textContent =
        exercise.title;

    elements.exerciseObjective.textContent =
        exercise.learner_goal ?? "";

    elements.exerciseScenario.textContent =
        exercise.scenario ?? "";

    elements.exerciseProblem.textContent =
        exercise.problem_statement ?? "";

    elements.exerciseInstructions.textContent =
        exercise.instructions ?? "";

    const restoredSubmission =
        typeof savedSubmission === "string";

    elements.codeEditor.value =
        restoredSubmission
            ? savedSubmission
            : (
                exercise.starter_code ??
                ""
              );

    updateLineNumbers();
    renderRevealedHints();

    elements.codeEditor.disabled =
        false;

    elements.resetStarterButton.disabled =
        false;

    elements.runGradeButton.disabled =
        false;

    elements.editorStatus.textContent =
        restoredSubmission
            ? (
                `Saved submission restored · ` +
                `${progress.attempt_count} attempt${
                    progress.attempt_count === 1
                        ? ""
                        : "s"
                }`
              )
            : exercise.id;

    elements.gradeSummary.textContent =
        "Not run yet";

    elements.gradeStages.innerHTML =
        `<div class="grade-empty-state">
            Run your solution to see structured grading stages.
         </div>`;

    elements.gradeOutput.textContent =
        "{}";

    elements.openLatestVisualizationButton.disabled =
        !Boolean(
            progress?.has_visualization
        );

    elements.openLatestVisualizationButton.textContent =
        progress?.has_visualization
            ? "Visualize last submission"
            : "Visualize this attempt";

    const gradePanel =
        elements.gradeOutput.closest(
            ".grade-panel"
        );

    gradePanel.classList.remove(
        "passed",
        "failed"
    );

    updateSolutionPanel(
        progress
    );
}

async function openExercise(exerciseId) {
    const metadata =
        exerciseById(
            exerciseId
        );

    if (!metadata) {
        return;
    }

    setActiveView(
        "exercise"
    );

    elements.exerciseTitle.textContent =
        metadata.title;

    elements.exerciseObjective.textContent =
        "Loading exercise…";

    elements.codeEditor.disabled =
        true;

    elements.resetStarterButton.disabled =
        true;

    elements.runGradeButton.disabled =
        true;

    try {
        const response =
            await fetch(
                exerciseUrl(
                    exerciseId
                ),
                {
                    cache: "no-store",
                }
            );

        const payload =
            await response.json();

        if (
            !response.ok ||
            !payload.ok ||
            !payload.exercise ||
            !payload.progress
        ) {
            throw new Error(
                payload.error ??
                "Exercise response is malformed."
            );
        }

        renderExerciseDocument(
            metadata,
            payload.exercise,
            payload.progress,
            payload.saved_submission
        );
    } catch (error) {
        elements.exerciseObjective.textContent =
            "Could not load exercise.";

        elements.gradeSummary.textContent =
            "Load error";

        elements.gradeStages.innerHTML =
            `<div class="grade-empty-state">
                ${escapeHtml(error.message)}
             </div>`;
    }
}

function handleEditorKeydown(event) {
    if (
        (
            event.ctrlKey ||
            event.metaKey
        ) &&
        event.key === "Enter"
    ) {
        event.preventDefault();

        runCurrentExercise();

        return;
    }

    if (event.key !== "Tab") {
        return;
    }

    event.preventDefault();

    const editor =
        elements.codeEditor;

    const start =
        editor.selectionStart;

    const end =
        editor.selectionEnd;

    const insertion = "    ";

    editor.value =
        editor.value.slice(
            0,
            start
        ) +
        insertion +
        editor.value.slice(
            end
        );

    editor.selectionStart =
        editor.selectionEnd =
            (
                start +
                insertion.length
            );

    updateLineNumbers();
}

async function runCurrentExercise() {
    if (
        !state.activeExerciseMetadata ||
        !state.activeExerciseDocument
    ) {
        return;
    }

    const source =
        elements.codeEditor.value;

    elements.runGradeButton.disabled =
        true;

    elements.resetStarterButton.disabled =
        true;

    elements.codeEditor.classList.add(
        "run-in-progress"
    );

    elements.editorStatus.textContent =
        "grading…";

    elements.gradeSummary.textContent =
        "Running compiler and tests…";

    elements.gradeStages.innerHTML =
        `<div class="grade-empty-state">
            Submitting to the local C++ Teacher grader…
         </div>`;

    elements.openLatestVisualizationButton.disabled =
        true;

    try {
        const response =
            await fetch(
                "/api/grade",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json",
                    },
                    body: JSON.stringify({
                        exercise_id:
                            state.activeExerciseMetadata.id,
                        source,
                    }),
                }
            );

        const result =
            await response.json();

        if (
            !response.ok ||
            !result.ok
        ) {
            throw new Error(
                result.error ??
                `HTTP ${response.status}`
            );
        }

        const grade =
            result.grade ?? null;

        elements.gradeOutput.textContent =
            grade
                ? JSON.stringify(
                    grade,
                    null,
                    2
                  )
                : "{}";

        renderGradeStages(
            grade,
            Boolean(
                result.timeline
            )
        );

        elements.gradeSummary.textContent =
            result.passed
                ? "PASS"
                : "NOT PASSED";

        const gradePanel =
            elements.gradeOutput.closest(
                ".grade-panel"
            );

        gradePanel.classList.toggle(
            "passed",
            result.passed
        );

        gradePanel.classList.toggle(
            "failed",
            !result.passed
        );

        state.latestGradeTimeline =
            result.timeline ?? null;

        state.activeExerciseProgress =
            result.progress;

        elements.editorStatus.textContent =
            (
                `Submission saved · ` +
                `${result.progress.attempt_count} attempt${
                    result.progress.attempt_count === 1
                        ? ""
                        : "s"
                }`
            );

        if (state.latestGradeTimeline) {
            elements.openLatestVisualizationButton.disabled =
                false;

            elements.openLatestVisualizationButton.textContent =
                "Visualize this attempt";
        }

        updateSolutionPanel(
            result.progress
        );

        await refreshLibraryData();
    } catch (error) {
        elements.gradeSummary.textContent =
            "Server error";

        elements.gradeStages.innerHTML =
            `<div class="grade-empty-state">
                ${escapeHtml(error.message)}
             </div>`;

        elements.gradeOutput.textContent =
            JSON.stringify(
                {
                    error:
                        error.message,
                },
                null,
                2
            );

        elements.gradeOutput.closest(
            ".grade-panel"
        ).classList.add(
            "failed"
        );
    } finally {
        elements.runGradeButton.disabled =
            false;

        elements.resetStarterButton.disabled =
            false;

        elements.codeEditor.classList.remove(
            "run-in-progress"
        );

        if (
            elements.editorStatus.textContent ===
            "grading…"
        ) {
            elements.editorStatus.textContent =
                state.activeExerciseDocument?.id ??
                "exercise";
        }
    }
}

function validateTimelineDocument(
    documentData
) {
    if (
        !documentData ||
        typeof documentData !== "object"
    ) {
        throw new Error(
            "Timeline JSON must contain an object."
        );
    }

    if (
        ![1, 2, 3, 4].includes(
            documentData.schema_version
        )
    ) {
        throw new Error(
            (
                "Unsupported schema_version: " +
                documentData.schema_version
            )
        );
    }

    if (
        !Array.isArray(
            documentData.timeline
        )
    ) {
        throw new Error(
            "Timeline JSON does not contain a timeline array."
        );
    }

    if (
        documentData.timeline.length === 0
    ) {
        throw new Error(
            "Timeline contains no snapshots."
        );
    }

    return documentData;
}

function showStatus(
    title,
    message,
    isError = false
) {
    elements.statusPanel.innerHTML = `
        <strong>
            ${escapeHtml(title)}
        </strong>

        <span>
            ${escapeHtml(message)}
        </span>
    `;

    elements.statusPanel.classList.toggle(
        "error",
        isError
    );

    elements.statusPanel.classList.remove(
        "hidden"
    );
}

function hideStatus() {
    elements.statusPanel.classList.add(
        "hidden"
    );
}

function loadDocument(
    documentData
) {
    stopPlayback();

    state.document =
        validateTimelineDocument(
            documentData
        );

    state.index = 0;

    elements.exerciseId.textContent =
        state.document.exercise_id ??
        "unknown";

    elements.schemaVersion.textContent =
        state.document.schema_version;

    elements.totalSteps.textContent =
        state.document.timeline.length;

    elements.timelineSlider.min = "0";

    elements.timelineSlider.max =
        String(
            state.document.timeline.length -
            1
        );

    elements.timelineSlider.value =
        "0";

    elements.visualizerApp.classList.remove(
        "hidden"
    );

    hideStatus();

    render();
}

function enterVisualization(
    timeline,
    kind
) {
    const title =
        state.activeExerciseMetadata?.title ??
        "Current exercise";

    state.currentVisualizationKind =
        kind;

    elements.visualizationExerciseTitle.textContent =
        kind === "solution"
            ? (
                `${title} — Reference Solution`
              )
            : (
                `${title} — Submission`
              );

    loadDocument(
        timeline
    );

    setActiveView(
        "visualizer"
    );
}

async function openAttemptVisualization() {
    if (!state.activeExerciseMetadata) {
        return;
    }

    if (state.latestGradeTimeline) {
        enterVisualization(
            state.latestGradeTimeline,
            "attempt"
        );

        return;
    }

    elements.openLatestVisualizationButton.disabled =
        true;

    try {
        const response =
            await fetch(
                latestAttemptVisualizationUrl(
                    state.activeExerciseMetadata.id
                ),
                {
                    cache: "no-store",
                }
            );

        const payload =
            await response.json();

        if (
            !response.ok ||
            !payload.ok ||
            !payload.timeline
        ) {
            throw new Error(
                payload.error ??
                "Visualization response is malformed."
            );
        }

        enterVisualization(
            payload.timeline,
            "attempt"
        );
    } catch (error) {
        elements.gradeSummary.textContent =
            "Visualization unavailable";

        elements.gradeStages.innerHTML =
            `<div class="grade-empty-state">
                ${escapeHtml(error.message)}
             </div>`;
    } finally {
        elements.openLatestVisualizationButton.disabled =
            !Boolean(
                state.activeExerciseProgress?.has_visualization
            );
    }
}

async function revealSolution() {
    if (
        !state.activeExerciseMetadata ||
        !state.activeExerciseProgress?.solution_available
    ) {
        return;
    }

    elements.viewSolutionButton.disabled =
        true;

    elements.viewSolutionButton.textContent =
        "Loading solution…";

    try {
        const response =
            await fetch(
                solutionRevealUrl(
                    state.activeExerciseMetadata.id
                ),
                {
                    method: "POST",
                }
            );

        const payload =
            await response.json();

        if (
            !response.ok ||
            !payload.ok ||
            !payload.available
        ) {
            throw new Error(
                payload.error ??
                "Solution is not available."
            );
        }

        state.activeExerciseProgress =
            payload.progress;

        elements.solutionCode.textContent =
            payload.solution;

        elements.solutionExplanation.textContent =
            payload.explanation ||
            "This is the validated reference implementation for the exercise.";

        elements.solutionContent.classList.remove(
            "hidden"
        );

        elements.solutionLockBadge.textContent =
            "Unlocked";

        elements.solutionLockBadge.className =
            "solution-lock-badge unlocked";

        elements.solutionMessage.textContent =
            "The reference solution is visible below. Compare it with your own reasoning before changing your code.";

        elements.viewSolutionButton.textContent =
            "Solution shown";

        await refreshLibraryData();
    } catch (error) {
        elements.solutionMessage.textContent =
            error.message;

        elements.viewSolutionButton.textContent =
            "View solution";
    } finally {
        elements.viewSolutionButton.disabled =
            false;
    }
}

async function visualizeSolution() {
    if (
        !state.activeExerciseMetadata
    ) {
        return;
    }

    elements.visualizeSolutionButton.disabled =
        true;

    elements.visualizeSolutionButton.textContent =
        "Generating visualization…";

    try {
        const response =
            await fetch(
                solutionVisualizationUrl(
                    state.activeExerciseMetadata.id
                ),
                {
                    method: "POST",
                }
            );

        const payload =
            await response.json();

        if (
            !response.ok ||
            !payload.ok ||
            !payload.timeline
        ) {
            throw new Error(
                payload.error ??
                "Solution visualization could not be generated."
            );
        }

        enterVisualization(
            payload.timeline,
            "solution"
        );
    } catch (error) {
        elements.solutionMessage.textContent =
            error.message;
    } finally {
        elements.visualizeSolutionButton.disabled =
            false;

        elements.visualizeSolutionButton.textContent =
            "Visualize solution";
    }
}

elements.exerciseCards.addEventListener(
    "click",
    async (event) => {
        const solveButton =
            event.target.closest(
                "[data-open-exercise]"
            );

        if (!solveButton) {
            return;
        }

        await openExercise(
            solveButton.dataset.openExercise
        );
    }
);

for (
    const control of [
        elements.exerciseSearch,
        elements.topicFilter,
        elements.difficultyFilter,
        elements.statusFilter,
    ]
) {
    control.addEventListener(
        control === elements.exerciseSearch
            ? "input"
            : "change",
        renderExerciseLibrary
    );
}

elements.clearFiltersButton.addEventListener(
    "click",
    () => {
        elements.exerciseSearch.value =
            "";

        elements.topicFilter.value =
            "all";

        elements.difficultyFilter.value =
            "all";

        elements.statusFilter.value =
            "all";

        renderExerciseLibrary();
    }
);

elements.backToLibraryButton.addEventListener(
    "click",
    async () => {
        await refreshLibraryData();

        setActiveView(
            "library"
        );
    }
);

elements.backToExerciseButton.addEventListener(
    "click",
    () => {
        if (
            state.activeExerciseMetadata &&
            state.activeExerciseDocument
        ) {
            setActiveView(
                "exercise"
            );

            return;
        }

        setActiveView(
            "library"
        );
    }
);

elements.revealHintButton.addEventListener(
    "click",
    () => {
        const hints =
            state.activeExerciseDocument?.hints ??
            [];

        if (
            state.revealedHintCount <
            hints.length
        ) {
            state.revealedHintCount += 1;

            renderRevealedHints();
        }
    }
);

elements.codeEditor.addEventListener(
    "keydown",
    handleEditorKeydown
);

elements.codeEditor.addEventListener(
    "input",
    updateLineNumbers
);

elements.codeEditor.addEventListener(
    "scroll",
    () => {
        elements.lineNumbers.scrollTop =
            elements.codeEditor.scrollTop;
    }
);

elements.resetStarterButton.addEventListener(
    "click",
    () => {
        if (
            state.activeExerciseDocument
        ) {
            elements.codeEditor.value =
                state.activeExerciseDocument.starter_code ??
                "";

            updateLineNumbers();
        }
    }
);

elements.runGradeButton.addEventListener(
    "click",
    runCurrentExercise
);

elements.openLatestVisualizationButton.addEventListener(
    "click",
    openAttemptVisualization
);

elements.viewSolutionButton.addEventListener(
    "click",
    revealSolution
);

elements.visualizeSolutionButton.addEventListener(
    "click",
    visualizeSolution
);

function render() {
    const snapshot =
        state.document.timeline[state.index];

    elements.currentStep.textContent =
        snapshot.step;

    elements.timelineSlider.value =
        String(state.index);

    elements.previousButton.disabled =
        state.index === 0;

    elements.nextButton.disabled =
        state.index === state.document.timeline.length - 1;

    renderEvent(snapshot.cause);
    renderScopes(snapshot.active_scopes ?? []);
    renderStackValues(snapshot.stack_values ?? [], snapshot);
    renderAliases(snapshot.aliases ?? []);
    renderStack(snapshot.stack ?? []);
    renderHeap(snapshot.heap ?? []);
    renderTeachingNote(snapshot);
    animateSnapshot();

    requestAnimationFrame(drawPointerArrows);
}

function renderEvent(cause) {
    elements.eventType.textContent =
        cause?.type ?? "UNKNOWN";

    elements.eventSubject.textContent =
        cause?.subject ?? "—";

    elements.eventDetail.textContent =
        cause?.detail ?? "—";
}

function findHeapResource(snapshot, resourceId) {
    return (snapshot.heap ?? []).find(
        (resource) => resource.id === resourceId
    );
}

function renderScopes(activeScopes) {
    elements.activeScopes.innerHTML = "";

    if (activeScopes.length === 0) {
        elements.activeScopes.innerHTML =
            `<span class="empty-state">No active scope.</span>`;
        return;
    }

    activeScopes.forEach((scope, index) => {
        if (index > 0) {
            const arrow = document.createElement("span");
            arrow.className = "scope-arrow";
            arrow.textContent = "→";
            elements.activeScopes.appendChild(arrow);
        }

        const chip = document.createElement("span");
        chip.className = "scope-chip";
        chip.textContent = scope;
        elements.activeScopes.appendChild(chip);
    });
}

function renderStackValues(values, snapshot) {
    elements.stackValues.innerHTML = "";

    if (values.length === 0) {
        elements.stackValues.innerHTML =
            `<div class="empty-state">No scalar stack storage yet.</div>`;
        return;
    }

    for (const value of values) {
        const card = document.createElement("article");

        card.className =
            `stack-value-card ${value.alive ? "" : "out-of-scope"}`;

        card.dataset.stackValueId =
            value.name;

        if (snapshot.cause?.type === "WRITE_VALUE" &&
            snapshot.cause?.subject === value.name) {
            card.classList.add("value-changed");
        }

        card.innerHTML = `
            <div class="value-card-body">
                <div class="value-identity">
                    <span class="value-name">
                        ${escapeHtml(value.name)}
                    </span>
                    <span class="value-type">
                        ${escapeHtml(value.type ?? "value")}
                    </span>
                    ${value.scope
                        ? `<span class="value-scope">scope: ${escapeHtml(value.scope)}</span>`
                        : ""}
                </div>

                <div class="stack-value">
                    ${escapeHtml(value.value ?? "—")}
                </div>
            </div>
        `;

        elements.stackValues.appendChild(card);
    }
}

function renderAliases(aliases) {
    elements.stackAliases.innerHTML = "";

    if (aliases.length === 0) {
        elements.stackAliases.innerHTML =
            `<div class="empty-state">No references bound yet.</div>`;
        return;
    }

    for (const alias of aliases) {
        const card = document.createElement("article");

        const constClass =
            alias.const ? "const-alias" : "";

        const aliveClass =
            alias.alive ? "" : "out-of-scope";

        card.className =
            `alias-card ${constClass} ${aliveClass}`;

        card.innerHTML = `
            <div class="alias-card-body">
                <div class="alias-identity">
                    <span class="alias-name">
                        ${escapeHtml(alias.name)}
                    </span>
                    <span class="alias-type">
                        ${escapeHtml(alias.type ?? "reference")}
                    </span>
                    ${alias.scope
                        ? `<span class="alias-scope">scope: ${escapeHtml(alias.scope)}</span>`
                        : ""}
                </div>

                <div>
                    <span class="alias-badge">
                        ${alias.const ? "read-only alias" : "writable alias"}
                    </span>

                    <span
                        class="alias-target"
                        data-alias-target="${escapeHtml(alias.target ?? "")}"
                        data-alias-const="${alias.const ? "true" : "false"}"
                        data-alias-alive="${alias.alive ? "true" : "false"}"
                    >
                        &amp; ${escapeHtml(alias.target ?? "—")}
                    </span>
                </div>
            </div>
        `;

        elements.stackAliases.appendChild(card);
    }
}

function renderStack(stackObjects) {
    elements.stackObjects.innerHTML = "";

    if (stackObjects.length === 0) {
        elements.stackObjects.innerHTML =
            `<div class="empty-state">No stack objects yet.</div>`;
        return;
    }

    for (const object of stackObjects) {
        const card = document.createElement("article");
        const lifetime =
            object.lifetime ??
            (object.alive ? "alive" : "destroyed");

        const scopeClass =
            object.scope
                ? `scope-${String(object.scope).replace(/[^a-zA-Z0-9_-]/g, "-")}`
                : "";

        card.className =
            `memory-object ${lifetime} ${scopeClass}`;

        let badgeClass = "state-alive";
        let badgeText = "alive";

        if (lifetime === "destroying") {
            badgeClass = "state-destroying";
            badgeText = "destroying";
        } else if (lifetime === "destroyed") {
            badgeClass = "state-dead";
            badgeText = "destroyed";
        }

        card.innerHTML = `
            <div class="object-header">
                <div>
                    <div class="object-name">
                        ${escapeHtml(object.name)}
                    </div>
                    <div class="object-type">
                        ${escapeHtml(object.type ?? "object")}
                    </div>
                    ${object.scope
                        ? `<div class="object-scope">scope: ${escapeHtml(object.scope)}</div>`
                        : ""}
                </div>

                <span class="state-badge ${badgeClass}">
                    ${badgeText}
                </span>
            </div>

            <div class="fields"></div>
        `;

        const fieldsContainer =
            card.querySelector(".fields");

        const fieldEntries =
            Object.entries(object.fields ?? {});

        if (fieldEntries.length === 0) {
            fieldsContainer.innerHTML =
                `<div class="empty-state">Object lifetime ended.</div>`;
        }

        for (const [fieldName, field] of fieldEntries) {
            const row =
                document.createElement("div");

            row.className = "field-row";

            if (field.kind === "pointer") {
                const target =
                    field.points_to;

                const snapshot =
                    state.document.timeline[state.index];

                const targetResource =
                    target
                        ? findHeapResource(snapshot, target)
                        : null;

                const dangling =
                    targetResource &&
                    targetResource.alive === false;

                const pointerClass =
                    target === null
                        ? "null"
                        : dangling
                            ? "dangling"
                            : "";

                row.innerHTML = `
                    <span class="field-name">
                        ${escapeHtml(fieldName)}
                    </span>

                    <span
                        class="pointer-value ${pointerClass}"
                        data-pointer-source="${escapeHtml(object.name)}.${escapeHtml(fieldName)}"
                        data-points-to="${escapeHtml(target ?? "")}"
                    >
                        <span class="pointer-dot"></span>
                        ${target === null
                            ? "nullptr"
                            : escapeHtml(target)}
                    </span>
                `;
            } else {
                row.innerHTML = `
                    <span class="field-name">
                        ${escapeHtml(fieldName)}
                    </span>

                    <span>
                        ${escapeHtml(field.value ?? "—")}
                    </span>
                `;
            }

            fieldsContainer.appendChild(row);
        }

        elements.stackObjects.appendChild(card);
    }
}

function renderHeap(heapResources) {
    elements.heapResources.innerHTML = "";

    if (heapResources.length === 0) {
        elements.heapResources.innerHTML =
            `<div class="empty-state">Heap is empty.</div>`;
        return;
    }

    for (const resource of heapResources) {
        const card = document.createElement("article");

        card.className =
            `heap-resource ${resource.alive ? "" : "freed"}`;

        card.dataset.resourceId =
            resource.id;

        const badgeClass =
            resource.alive ? "state-alive" : "state-dead";

        const badgeText =
            resource.alive ? "allocated" : "freed";

        card.innerHTML = `
            <div class="resource-header">
                <span class="resource-id">
                    ${escapeHtml(resource.id)}
                </span>

                <span class="state-badge ${badgeClass}">
                    ${badgeText}
                </span>
            </div>

            <div class="resource-body">
                <div class="resource-value">
                    value =
                    <strong>${escapeHtml(resource.value ?? "—")}</strong>
                </div>
            </div>
        `;

        elements.heapResources.appendChild(card);
    }
}

function renderTeachingNote(snapshot) {
    const type =
        snapshot.cause?.type ?? "";

    const notes = {
        ENTER_SCOPE: [
            "Scope entered",
            "A new lexical scope is active. Stack values and references declared here remain valid until this scope ends."
        ],

        CREATE_VALUE: [
            "Stack storage created",
            "The variable owns one int-sized piece of stack storage. References created later will alias this storage rather than create another int."
        ],

        BIND_ALIAS: [
            "Reference bound",
            "A C++ reference becomes another name for existing storage. No second integer is created."
        ],

        WRITE_VALUE: [
            "Write through an alias",
            "Assigning through the non-const reference updates the original storage itself. Every alias observes the same new value."
        ],

        EXIT_SCOPE: [
            "Scope exited",
            "All automatic objects belonging to this scope have already been destroyed in reverse construction order."
        ],

        CREATE_OBJECT: [
            "Object lifetime begins",
            "A stack object now exists inside the current scope. RAII ties resource cleanup to this object's lifetime."
        ],

        ALLOCATE_RESOURCE: [
            "Heap allocation",
            "A new heap resource exists. The next pointer-binding event shows which object owns or references it."
        ],

        BIND_POINTER: [
            "Pointer binding",
            "A pointer field now stores the identity of a heap resource, creating a visible stack-to-heap relationship."
        ],

        MOVE_RESOURCE: [
            "Transfer in progress",
            "The destination pointer now stores the same resource address. Before the source is cleared, both raw pointer fields temporarily reference that allocation."
        ],

        SET_NULL: [
            "Ownership transfer completed",
            "The moved-from source pointer has been cleared. The destination remains connected to the original heap resource."
        ],

        FREE_RESOURCE: [
            "Resource lifetime ends",
            "The heap allocation has been freed. If a still-live pointer visually targets it, that pointer is temporarily dangling during destructor execution."
        ],

        DESTROY_BEGIN: [
            "Destructor execution begins",
            "The object is still alive while its destructor runs. Its members can be released during this phase."
        ],

        DESTROY_END: [
            "Object lifetime ends",
            "The destructor has completed. The stack object's fields are no longer part of the live program state."
        ],

        DESTROY_OBJECT: [
            "Object lifetime ends",
            "This legacy event marks the object as fully destroyed."
        ],

        WARNING: [
            "Runtime warning",
            "The runtime trace detected a suspicious ownership or lifetime condition."
        ]
    };

    let [title, text] =
        notes[type] ?? [
            "Memory state updated",
            "Inspect how the stack and heap changed after this event."
        ];

    if (
        type === "MOVE_RESOURCE" &&
        String(snapshot.cause?.detail ?? "")
            .includes("transfer=exclusive")
    ) {
        title =
            "Exclusive ownership transferred";

        text =
            "The destination now owns the original heap resource and the moved-from source is empty. No second resource allocation is needed.";
    }

    elements.teachingTitle.textContent = title;
    elements.teachingText.textContent = text;
}

function drawPointerArrows() {
    const svg =
        elements.arrowLayer;

    const stageRect =
        elements.memoryStage.getBoundingClientRect();

    svg.setAttribute(
        "viewBox",
        `0 0 ${stageRect.width} ${stageRect.height}`
    );

    svg.innerHTML = `
        <defs>
            <marker
                id="arrowHead"
                markerWidth="10"
                markerHeight="10"
                refX="9"
                refY="3"
                orient="auto"
                markerUnits="strokeWidth"
            >
                <path
                    d="M0,0 L0,6 L9,3 z"
                    class="arrow-head"
                />
            </marker>
            <marker
                id="aliasArrowHead"
                markerWidth="10"
                markerHeight="10"
                refX="9"
                refY="3"
                orient="auto"
                markerUnits="strokeWidth"
            >
                <path
                    d="M0,0 L0,6 L9,3 z"
                    class="alias-arrow-head"
                />
            </marker>

            <marker
                id="constAliasArrowHead"
                markerWidth="10"
                markerHeight="10"
                refX="9"
                refY="3"
                orient="auto"
                markerUnits="strokeWidth"
            >
                <path
                    d="M0,0 L0,6 L9,3 z"
                    class="const-alias-arrow-head"
                />
            </marker>
        </defs>
    `;

    const snapshot =
        state.document.timeline[state.index];

    const pointerElements =
        elements.stackObjects.querySelectorAll(
            "[data-points-to]"
        );

    for (const sourceElement of pointerElements) {
        const targetId =
            sourceElement.dataset.pointsTo;

        if (!targetId) {
            continue;
        }

        const targetElement =
            elements.heapResources.querySelector(
                `[data-resource-id="${CSS.escape(targetId)}"]`
            );

        if (!targetElement) {
            continue;
        }

        const sourceRect =
            sourceElement.getBoundingClientRect();

        const targetRect =
            targetElement.getBoundingClientRect();

        const startX =
            sourceRect.right - stageRect.left;

        const startY =
            sourceRect.top +
            sourceRect.height / 2 -
            stageRect.top;

        const endX =
            targetRect.left - stageRect.left;

        const endY =
            targetRect.top +
            targetRect.height / 2 -
            stageRect.top;

        const controlOffset =
            Math.max(55, (endX - startX) * 0.45);

        const path =
            document.createElementNS(
                "http://www.w3.org/2000/svg",
                "path"
            );

        path.setAttribute(
            "d",
            [
                `M ${startX} ${startY}`,
                `C ${startX + controlOffset} ${startY},`,
                `${endX - controlOffset} ${endY},`,
                `${endX} ${endY}`
            ].join(" ")
        );

        const targetResource =
            findHeapResource(snapshot, targetId);

        const dangling =
            targetResource &&
            targetResource.alive === false;

        path.setAttribute(
            "class",
            `pointer-arrow ${dangling ? "dangling" : ""}`
        );

        path.setAttribute(
            "marker-end",
            "url(#arrowHead)"
        );

        svg.appendChild(path);

        // Animate the pointer line into the new snapshot.
        const length = path.getTotalLength();

        path.style.strokeDasharray = `${length}`;
        path.style.strokeDashoffset = `${length}`;

        requestAnimationFrame(() => {
            path.style.strokeDashoffset = "0";
        });
    }

    const aliasElements =
        elements.stackAliases.querySelectorAll(
            "[data-alias-target]"
        );

    for (const sourceElement of aliasElements) {
        const targetName =
            sourceElement.dataset.aliasTarget;

        const aliasAlive =
            sourceElement.dataset.aliasAlive === "true";

        if (!targetName || !aliasAlive) {
            continue;
        }

        const targetElement =
            elements.stackValues.querySelector(
                `[data-stack-value-id="${CSS.escape(targetName)}"]`
            );

        if (!targetElement) {
            continue;
        }

        const sourceRect =
            sourceElement.getBoundingClientRect();

        const targetRect =
            targetElement.getBoundingClientRect();

        const startX =
            sourceRect.right - stageRect.left;

        const startY =
            sourceRect.top +
            sourceRect.height / 2 -
            stageRect.top;

        const endX =
            targetRect.right - stageRect.left;

        const endY =
            targetRect.top +
            targetRect.height / 2 -
            stageRect.top;

        const curveX =
            Math.max(startX, endX) + 52;

        const path =
            document.createElementNS(
                "http://www.w3.org/2000/svg",
                "path"
            );

        path.setAttribute(
            "d",
            [
                `M ${startX} ${startY}`,
                `C ${curveX} ${startY},`,
                `${curveX} ${endY},`,
                `${endX} ${endY}`
            ].join(" ")
        );

        const isConst =
            sourceElement.dataset.aliasConst === "true";

        path.setAttribute(
            "class",
            `alias-arrow ${isConst ? "const-reference" : ""}`
        );

        path.setAttribute(
            "marker-end",
            isConst
                ? "url(#constAliasArrowHead)"
                : "url(#aliasArrowHead)"
        );

        svg.appendChild(path);

        const length =
            path.getTotalLength();

        path.style.strokeDasharray =
            `${length}`;

        path.style.strokeDashoffset =
            `${length}`;

        requestAnimationFrame(() => {
            path.style.strokeDashoffset = "0";
        });
    }
}

function animateSnapshot() {
    const cards = document.querySelectorAll(
        ".memory-object, .heap-resource, .stack-value-card, .alias-card"
    );

    for (const card of cards) {
        card.classList.remove("snapshot-enter");

        // Force a new animation even when navigating quickly.
        void card.offsetWidth;

        card.classList.add("snapshot-enter");
    }

    const eventCard = document.querySelector(".event-card");

    eventCard.classList.remove("event-pulse");
    void eventCard.offsetWidth;
    eventCard.classList.add("event-pulse");
}

function stopPlayback() {
    if (state.playTimer !== null) {
        window.clearInterval(state.playTimer);
        state.playTimer = null;
    }

    if (elements.playButton) {
        elements.playButton.textContent = "▶ Play";
        elements.playButton.classList.remove("playing");
    }
}

function startPlayback() {
    if (!state.document) {
        return;
    }

    if (state.index >= state.document.timeline.length - 1) {
        state.index = 0;
        render();
    }

    elements.playButton.textContent = "❚❚ Pause";
    elements.playButton.classList.add("playing");

    state.playTimer = window.setInterval(() => {
        if (state.index >= state.document.timeline.length - 1) {
            stopPlayback();
            return;
        }

        state.index += 1;
        render();
    }, 1100);
}

function togglePlayback() {
    if (state.playTimer !== null) {
        stopPlayback();
    } else {
        startPlayback();
    }
}

function goToIndex(index) {
    if (!state.document) {
        return;
    }

    const max =
        state.document.timeline.length - 1;

    state.index =
        Math.max(0, Math.min(index, max));

    render();
}


elements.previousButton.addEventListener(
    "click",
    () => goToIndex(state.index - 1)
);

elements.nextButton.addEventListener(
    "click",
    () => goToIndex(state.index + 1)
);

elements.playButton.addEventListener(
    "click",
    togglePlayback
);

elements.timelineSlider.addEventListener(
    "input",
    () => {
        stopPlayback();

        goToIndex(
            Number(
                elements.timelineSlider.value
            )
        );
    }
);

window.addEventListener(
    "resize",
    () => {
        if (
            state.activeView === "visualizer" &&
            state.document
        ) {
            requestAnimationFrame(
                drawPointerArrows
            );
        }
    }
);

setActiveView("library");
loadExerciseLibrary();
