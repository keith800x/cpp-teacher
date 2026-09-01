const authoringElements = {
    openButton: document.querySelector("#openAuthoringButton"),
    backButton: document.querySelector("#backFromAuthoringButton"),
    environmentStatus: document.querySelector("#authoringEnvironmentStatus"),
    topic: document.querySelector("#authoringTopic"),
    difficulty: document.querySelector("#authoringDifficulty"),
    model: document.querySelector("#authoringModel"),
    repairs: document.querySelector("#authoringRepairs"),
    generateButton: document.querySelector("#generateExerciseButton"),
    generationStatus: document.querySelector("#generationStatus"),
    generationLog: document.querySelector("#generationLog"),
    refreshButton: document.querySelector("#refreshAuthoringButton"),
    candidates: document.querySelector("#authoringCandidates"),
    published: document.querySelector("#publishedExerciseList"),
};

const authoringState = {
    status: null,
    busy: false,
};

function authoringEscape(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

async function authoringRequest(url, options = {}) {
    const response = await fetch(
        url,
        {
            cache: "no-store",
            ...options,
        }
    );

    let payload = null;

    try {
        payload = await response.json();
    } catch {
        payload = {
            ok: false,
            error: `HTTP ${response.status}`,
        };
    }

    if (!response.ok || !payload.ok) {
        const error = new Error(
            payload.error ??
            `HTTP ${response.status}`
        );

        error.payload = payload;
        throw error;
    }

    return payload;
}

function authoringStatusBadge(candidate) {
    if (candidate.validation_stale) {
        return `<span class="authoring-badge pending">Needs revalidation</span>`;
    }

    if (candidate.published) {
        return `<span class="authoring-badge published">Published</span>`;
    }

    if (candidate.valid) {
        return `<span class="authoring-badge valid">Valid</span>`;
    }

    if (candidate.validation) {
        return `<span class="authoring-badge invalid">Invalid</span>`;
    }

    return `<span class="authoring-badge pending">Not validated</span>`;
}

function authoringSafeFilenamePart(value) {
    const cleaned = String(value ?? "")
        .trim()
        .replace(/[^A-Za-z0-9._-]+/g, "_")
        .replace(/^_+|_+$/g, "");

    return cleaned || "candidate";
}

function authoringDownloadBlob(
    filename,
    content,
    mimeType
) {
    const blob = new Blob(
        [content],
        {
            type: mimeType,
        }
    );

    const url = URL.createObjectURL(
        blob
    );

    const link = document.createElement(
        "a"
    );

    link.href = url;
    link.download = filename;
    link.style.display = "none";

    document.body.appendChild(
        link
    );

    link.click();
    link.remove();

    window.setTimeout(
        () => URL.revokeObjectURL(
            url
        ),
        0
    );
}

function buildValidationDownloadDocument(
    payload,
    candidateId
) {
    const candidate = payload.candidate ?? {};
    const exercise = candidate.exercise ?? {};
    const generationMetadata =
        candidate.generation_metadata ?? {};
    const validation = payload.validation ?? null;

    return {
        report_format_version: 1,
        report_type:
            "cpp_teacher_candidate_validation",
        downloaded_at:
            new Date().toISOString(),
        candidate_id:
            exercise.id ??
            candidateId,
        title:
            exercise.title ??
            "",
        topic:
            exercise.topic ??
            "",
        difficulty:
            exercise.difficulty ??
            "",
        validation_stale:
            Boolean(
                payload.validation_stale
            ),
        generation_metadata:
            generationMetadata,
        validation,
    };
}

function validationReportAsText(
    report
) {
    const validation =
        report.validation ?? {};

    const checks = Array.isArray(
        validation.checks
    )
        ? validation.checks
        : [];

    const failures = Number(
        validation.failure_count ?? 0
    );

    const warnings = Number(
        validation.warning_count ?? 0
    );

    const valid =
        validation.valid === true;

    const lines = [
        "C++ Teacher validation report",
        "",
        `Candidate: ${report.candidate_id}`,
        `Title: ${report.title}`,
        `Topic: ${report.topic}`,
        `Difficulty: ${report.difficulty}`,
        (
            "Validation state: " +
            (
                report.validation_stale
                    ? "STALE"
                    : (
                        valid
                            ? "VALID"
                            : "INVALID"
                    )
            )
        ),
        `Failures: ${failures}`,
        `Warnings: ${warnings}`,
        (
            "Validator version: " +
            (
                validation.validator_version ??
                "unknown"
            )
        ),
        (
            "Generation attempt: " +
            (
                report.generation_metadata
                    ?.generation_attempt ??
                "unknown"
            )
        ),
        (
            "Model: " +
            (
                report.generation_metadata
                    ?.model ??
                "unknown"
            )
        ),
        `Downloaded: ${report.downloaded_at}`,
        "",
        "Checks",
        "------",
    ];

    if (!checks.length) {
        lines.push(
            "No validation checks are available."
        );
    } else {
        for (const check of checks) {
            const status = String(
                check.status ?? "unknown"
            ).toUpperCase();

            const category = String(
                check.category ?? ""
            ).trim();

            const checkId = String(
                check.id ?? "unknown"
            );

            const qualifiedId = category
                ? `${category}/${checkId}`
                : checkId;

            lines.push(
                `[${status}] ${qualifiedId}: ${check.message ?? ""}`
            );
        }
    }

    return (
        lines.join(
            "\n"
        ) +
        "\n"
    );
}

async function fetchAuthoringCandidate(
    candidateId
) {
    return authoringRequest(
        `/api/authoring/candidates/${encodeURIComponent(candidateId)}`
    );
}

async function downloadValidationReport(
    candidateId,
    format
) {
    const payload =
        await fetchAuthoringCandidate(
            candidateId
        );

    if (!payload.validation) {
        throw new Error(
            `${candidateId} has no validation report to download.`
        );
    }

    const report =
        buildValidationDownloadDocument(
            payload,
            candidateId
        );

    const safeId =
        authoringSafeFilenamePart(
            candidateId
        );

    if (format === "txt") {
        authoringDownloadBlob(
            `validation-${safeId}.txt`,
            validationReportAsText(
                report
            ),
            "text/plain;charset=utf-8"
        );

        return;
    }

    if (format === "json") {
        authoringDownloadBlob(
            `validation-${safeId}.json`,
            (
                JSON.stringify(
                    report,
                    null,
                    2
                ) +
                "\n"
            ),
            "application/json;charset=utf-8"
        );

        return;
    }

    throw new Error(
        `Unsupported report format: ${format}`
    );
}

async function downloadCandidateBundle(
    candidateId
) {
    const payload =
        await fetchAuthoringCandidate(
            candidateId
        );

    if (!payload.candidate) {
        throw new Error(
            `${candidateId} candidate data is unavailable.`
        );
    }

    const safeId =
        authoringSafeFilenamePart(
            candidateId
        );

    authoringDownloadBlob(
        `candidate-${safeId}.json`,
        (
            JSON.stringify(
                payload.candidate,
                null,
                2
            ) +
            "\n"
        ),
        "application/json;charset=utf-8"
    );
}

function validationSummary(validation, stale = false) {
    if (stale) {
        return "Validation report is older than the current validator.";
    }

    if (!validation) {
        return "No validation report yet.";
    }

    const failures = Number(
        validation.failure_count ?? 0
    );

    const warnings = Number(
        validation.warning_count ?? 0
    );

    if (validation.valid) {
        return `0 failures · ${warnings} warning${warnings === 1 ? "" : "s"}`;
    }

    return `${failures} failure${failures === 1 ? "" : "s"} · ${warnings} warning${warnings === 1 ? "" : "s"}`;
}

function renderAuthoringEnvironment(status) {
    const keyText = status.api_key_configured
        ? "API key configured"
        : "OPENAI_API_KEY missing";

    const graderText = status.grader_built
        ? "grader ready"
        : "grader unavailable";

    authoringElements.environmentStatus.textContent =
        `${keyText} · ${graderText} · model ${status.model}`;

    authoringElements.environmentStatus.classList.toggle(
        "error",
        !status.api_key_configured ||
        !status.grader_built
    );

    authoringElements.generateButton.disabled =
        !status.api_key_configured ||
        !status.grader_built ||
        authoringState.busy;
}

function populateAuthoringTopics(status) {
    const selected = authoringElements.topic.value;

    authoringElements.topic.innerHTML = "";

    for (const topic of status.topics ?? []) {
        const option = document.createElement("option");

        option.value = topic.id;
        option.textContent =
            topic.display_name ??
            topic.id;

        authoringElements.topic.appendChild(option);
    }

    if (
        selected &&
        [...authoringElements.topic.options].some(
            (option) => option.value === selected
        )
    ) {
        authoringElements.topic.value = selected;
    }

    if (
        !authoringElements.model.value &&
        status.model
    ) {
        authoringElements.model.value = status.model;
    }
}

function renderAuthoringCandidates(candidates) {
    authoringElements.candidates.innerHTML = "";

    if (!candidates?.length) {
        authoringElements.candidates.innerHTML = `
            <div class="authoring-empty-state">
                No AI candidates yet. Generate one above.
            </div>
        `;
        return;
    }

    for (const candidate of candidates) {
        const card = document.createElement("article");
        card.className = "authoring-card";
        card.dataset.candidateId = candidate.id;

        const meta = candidate.generation_metadata ?? {};

        card.innerHTML = `
            <div class="authoring-card-header">
                <div>
                    <div class="authoring-card-badges">
                        ${authoringStatusBadge(candidate)}
                        <span class="topic-badge">${authoringEscape(topicLabel(candidate.topic))}</span>
                        <span class="difficulty-badge ${authoringEscape(candidate.difficulty)}">
                            ${authoringEscape(difficultyLabel(candidate.difficulty))}
                        </span>
                    </div>
                    <h4>${authoringEscape(candidate.title)}</h4>
                </div>
                <span class="authoring-candidate-id">${authoringEscape(candidate.id)}</span>
            </div>

            <p class="authoring-card-goal">
                ${authoringEscape(candidate.learner_goal)}
            </p>

            <p class="authoring-card-scenario">
                ${authoringEscape(candidate.scenario)}
            </p>

            <div class="authoring-card-meta">
                <span>${authoringEscape(validationSummary(candidate.validation, candidate.validation_stale))}</span>
                <span>Generation call ${authoringEscape(meta.generation_attempt ?? "—")}</span>
                <span>${authoringEscape(meta.model ?? "")}</span>
            </div>

            <div class="authoring-card-actions">
                <button
                    class="file-button"
                    type="button"
                    data-authoring-action="inspect"
                >
                    Inspect
                </button>
                <button
                    class="file-button"
                    type="button"
                    data-authoring-action="validate"
                >
                    Revalidate
                </button>
                <button
                    class="file-button"
                    type="button"
                    data-authoring-action="repair"
                    ${
                        !candidate.valid &&
                        candidate.validation &&
                        !candidate.validation_stale &&
                        !candidate.published
                            ? ""
                            : "disabled"
                    }
                >
                    Repair with AI
                </button>
                <button
                    class="primary-button"
                    type="button"
                    data-authoring-action="publish"
                    ${candidate.valid && !candidate.published ? "" : "disabled"}
                >
                    ${candidate.published ? "Published" : "Publish"}
                </button>
            </div>

            <div class="authoring-card-actions authoring-download-actions">
                <span class="authoring-download-label">Downloads</span>
                <button
                    class="file-button"
                    type="button"
                    data-authoring-action="download-report-txt"
                    ${candidate.validation ? "" : "disabled"}
                    title="Download a human-readable validation report"
                >
                    Report TXT
                </button>
                <button
                    class="file-button"
                    type="button"
                    data-authoring-action="download-report-json"
                    ${candidate.validation ? "" : "disabled"}
                    title="Download the machine-readable validation report"
                >
                    Report JSON
                </button>
                <button
                    class="file-button"
                    type="button"
                    data-authoring-action="download-candidate-json"
                    title="Download the candidate exercise and bundled hidden artifacts"
                >
                    Candidate JSON
                </button>
            </div>

            <div class="authoring-inspection hidden"></div>
        `;

        authoringElements.candidates.appendChild(card);
    }
}

function renderPublishedExercises(exercises) {
    authoringElements.published.innerHTML = "";

    if (!exercises?.length) {
        authoringElements.published.innerHTML = `
            <div class="authoring-empty-state">
                No published exercises.
            </div>
        `;
        return;
    }

    for (const exercise of exercises) {
        const row = document.createElement("article");
        row.className = "published-exercise-row";

        row.innerHTML = `
            <div>
                <div class="authoring-card-badges">
                    <span class="topic-badge">${authoringEscape(topicLabel(exercise.topic))}</span>
                    <span class="difficulty-badge ${authoringEscape(exercise.difficulty)}">
                        ${authoringEscape(difficultyLabel(exercise.difficulty))}
                    </span>
                    <span class="authoring-badge ${exercise.ai_generated ? "valid" : "pending"}">
                        ${exercise.ai_generated ? "AI generated" : "Hand-authored"}
                    </span>
                </div>
                <strong>${authoringEscape(exercise.title)}</strong>
                <span class="published-exercise-id">${authoringEscape(exercise.id)}</span>
            </div>

            <button
                class="danger-button"
                type="button"
                data-unpublish-exercise="${authoringEscape(exercise.id)}"
                data-ai-generated="${exercise.ai_generated ? "true" : "false"}"
            >
                Unpublish
            </button>
        `;

        authoringElements.published.appendChild(row);
    }
}

async function loadAuthoringStatus() {
    const payload = await authoringRequest(
        "/api/authoring/status"
    );

    authoringState.status = payload;

    renderAuthoringEnvironment(payload);
    populateAuthoringTopics(payload);
    renderAuthoringCandidates(payload.candidates ?? []);
    renderPublishedExercises(payload.published_exercises ?? []);
}

function setAuthoringBusy(busy, message = "") {
    authoringState.busy = busy;

    if (message) {
        authoringElements.generationStatus.textContent = message;
    }

    if (authoringState.status) {
        renderAuthoringEnvironment(
            authoringState.status
        );
    } else {
        authoringElements.generateButton.disabled = busy;
    }

    authoringElements.refreshButton.disabled = busy;
}

function renderValidationChecks(validation) {
    if (!validation?.checks?.length) {
        return `<p>No validation details available.</p>`;
    }

    return `
        <div class="authoring-validation-list">
            ${validation.checks.map((check) => `
                <div class="authoring-validation-row ${authoringEscape(check.status)}">
                    <strong>${authoringEscape(check.status.toUpperCase())}</strong>
                    <span>${authoringEscape(check.id)}</span>
                    <p>${authoringEscape(check.message)}</p>
                </div>
            `).join("")}
        </div>
    `;
}

async function inspectCandidate(card, candidateId) {
    const panel = card.querySelector(
        ".authoring-inspection"
    );

    if (!panel.classList.contains("hidden")) {
        panel.classList.add("hidden");
        panel.innerHTML = "";
        return;
    }

    panel.classList.remove("hidden");
    panel.innerHTML = "Loading candidate…";

    try {
        const payload = await authoringRequest(
            `/api/authoring/candidates/${encodeURIComponent(candidateId)}`
        );

        const exercise = payload.candidate?.exercise ?? {};
        const files = payload.candidate?.files ?? {};

        panel.innerHTML = `
            <div class="candidate-inspection-grid">
                <section>
                    <span class="label">Learner goal</span>
                    <p>${authoringEscape(exercise.learner_goal ?? exercise.problem_statement ?? candidateId)}</p>
                </section>
                <section>
                    <span class="label">Scenario</span>
                    <p>${authoringEscape(exercise.scenario ?? "")}</p>
                </section>
                <section>
                    <span class="label">Problem statement</span>
                    <p>${authoringEscape(exercise.problem_statement ?? "")}</p>
                </section>
                <section>
                    <span class="label">Internal learning objective</span>
                    <p>${authoringEscape(exercise.learning_objective ?? "")}</p>
                </section>
            </div>

            <details open>
                <summary>Starter code</summary>
                <pre>${authoringEscape(exercise.starter_code ?? "")}</pre>
            </details>

            <details>
                <summary>Hidden reference solution</summary>
                <pre>${authoringEscape(exercise.reference_solution ?? "")}</pre>
            </details>

            <details>
                <summary>Hidden artifacts (${Object.keys(files).length})</summary>
                ${Object.entries(files).map(([path, content]) => `
                    <div class="authoring-hidden-file">
                        <strong>${authoringEscape(path)}</strong>
                        <pre>${authoringEscape(content)}</pre>
                    </div>
                `).join("")}
            </details>

            <details>
                <summary>Validation report</summary>
                ${renderValidationChecks(payload.validation)}
            </details>
        `;
    } catch (error) {
        panel.innerHTML = `
            <div class="authoring-error">
                ${authoringEscape(error.message)}
            </div>
        `;
    }
}

async function generateExerciseFromUi() {
    setAuthoringBusy(
        true,
        "Generating and validating… this can take a minute."
    );

    authoringElements.generationLog.classList.add("hidden");
    authoringElements.generationLog.textContent = "";

    try {
        const payload = await authoringRequest(
            "/api/authoring/generate",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    topic: authoringElements.topic.value,
                    difficulty: authoringElements.difficulty.value,
                    model: authoringElements.model.value.trim(),
                    max_repairs: Number(
                        authoringElements.repairs.value
                    ),
                }),
            }
        );

        authoringElements.generationLog.textContent =
            payload.log ?? "";
        authoringElements.generationLog.classList.remove("hidden");

        if (payload.candidate) {
            authoringElements.generationStatus.textContent =
                payload.valid
                    ? `Validated: ${payload.candidate.title}`
                    : `Generated but still invalid: ${payload.candidate.title}`;
        } else {
            authoringElements.generationStatus.textContent =
                "Generation finished without a candidate.";
        }

        await loadAuthoringStatus();
    } catch (error) {
        authoringElements.generationStatus.textContent =
            error.message;

        if (error.payload?.log) {
            authoringElements.generationLog.textContent =
                error.payload.log;
            authoringElements.generationLog.classList.remove("hidden");
        }
    } finally {
        setAuthoringBusy(false);
    }
}

async function revalidateCandidate(candidateId) {
    setAuthoringBusy(
        true,
        `Validating ${candidateId}…`
    );

    try {
        const payload = await authoringRequest(
            "/api/authoring/validate",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    candidate_id: candidateId,
                }),
            }
        );

        authoringElements.generationStatus.textContent =
            payload.valid
                ? `${candidateId} is valid.`
                : `${candidateId} is invalid.`;

        await loadAuthoringStatus();
    } catch (error) {
        authoringElements.generationStatus.textContent =
            error.message;
    } finally {
        setAuthoringBusy(false);
    }
}

async function repairCandidate(candidateId) {
    setAuthoringBusy(
        true,
        `Repairing ${candidateId} with validator feedback…`
    );

    authoringElements.generationLog.classList.add(
        "hidden"
    );

    authoringElements.generationLog.textContent = "";

    try {
        const payload = await authoringRequest(
            "/api/authoring/repair",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    candidate_id: candidateId,
                    model: authoringElements.model.value.trim(),
                    max_repairs: Number(
                        authoringElements.repairs.value
                    ),
                }),
            }
        );

        authoringElements.generationLog.textContent =
            payload.log ?? "";

        authoringElements.generationLog.classList.remove(
            "hidden"
        );

        authoringElements.generationStatus.textContent =
            payload.valid
                ? `Repaired and validated: ${payload.candidate?.title ?? candidateId}`
                : `Repair attempts exhausted; ${payload.candidate?.title ?? candidateId} is still invalid.`;

        await loadAuthoringStatus();
    } catch (error) {
        authoringElements.generationStatus.textContent =
            error.message;

        if (error.payload?.log) {
            authoringElements.generationLog.textContent =
                error.payload.log;

            authoringElements.generationLog.classList.remove(
                "hidden"
            );
        }
    } finally {
        setAuthoringBusy(false);
    }
}


async function publishCandidate(candidateId) {
    if (!window.confirm(
        `Publish ${candidateId} to the exercise library?`
    )) {
        return;
    }

    setAuthoringBusy(
        true,
        `Publishing ${candidateId}…`
    );

    try {
        await authoringRequest(
            "/api/authoring/publish",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    candidate_id: candidateId,
                }),
            }
        );

        authoringElements.generationStatus.textContent =
            `${candidateId} published.`;

        await loadAuthoringStatus();
        await refreshLibraryData();
    } catch (error) {
        authoringElements.generationStatus.textContent =
            error.message;
    } finally {
        setAuthoringBusy(false);
    }
}

async function unpublishExercise(exerciseId, aiGenerated) {
    let warning =
        `Unpublish ${exerciseId}? It will disappear from the exercise library, but its source files and saved progress will be kept.`;

    if (!aiGenerated) {
        warning +=
            " This is hand-authored, so it will not have an AI candidate Publish button unless you restore its catalog entry manually.";
    }

    if (!window.confirm(warning)) {
        return;
    }

    setAuthoringBusy(
        true,
        `Unpublishing ${exerciseId}…`
    );

    try {
        await authoringRequest(
            "/api/authoring/unpublish",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    exercise_id: exerciseId,
                    delete_progress: false,
                }),
            }
        );

        authoringElements.generationStatus.textContent =
            `${exerciseId} unpublished.`;

        await loadAuthoringStatus();
        await refreshLibraryData();
    } catch (error) {
        authoringElements.generationStatus.textContent =
            error.message;
    } finally {
        setAuthoringBusy(false);
    }
}

authoringElements.openButton.addEventListener(
    "click",
    async () => {
        setActiveView("authoring");
        authoringElements.generationStatus.textContent =
            "Loading authoring workspace…";

        try {
            await loadAuthoringStatus();
            authoringElements.generationStatus.textContent =
                "Ready.";
        } catch (error) {
            authoringElements.generationStatus.textContent =
                error.message;
        }
    }
);

authoringElements.backButton.addEventListener(
    "click",
    async () => {
        await refreshLibraryData();
        setActiveView("library");
    }
);

authoringElements.refreshButton.addEventListener(
    "click",
    async () => {
        try {
            await loadAuthoringStatus();
            authoringElements.generationStatus.textContent =
                "Authoring data refreshed.";
        } catch (error) {
            authoringElements.generationStatus.textContent =
                error.message;
        }
    }
);

authoringElements.generateButton.addEventListener(
    "click",
    generateExerciseFromUi
);

authoringElements.candidates.addEventListener(
    "click",
    async (event) => {
        const button = event.target.closest(
            "[data-authoring-action]"
        );

        if (!button || authoringState.busy) {
            return;
        }

        const card = button.closest(
            "[data-candidate-id]"
        );

        if (!card) {
            return;
        }

        const candidateId = card.dataset.candidateId;
        const action = button.dataset.authoringAction;

        if (action === "inspect") {
            await inspectCandidate(
                card,
                candidateId
            );
        } else if (action === "validate") {
            await revalidateCandidate(
                candidateId
            );
        } else if (action === "repair") {
            await repairCandidate(
                candidateId
            );
        } else if (action === "publish") {
            await publishCandidate(
                candidateId
            );
        } else if (action === "download-report-txt") {
            try {
                await downloadValidationReport(
                    candidateId,
                    "txt"
                );

                authoringElements.generationStatus.textContent =
                    `Downloaded validation TXT for ${candidateId}.`;
            } catch (error) {
                authoringElements.generationStatus.textContent =
                    error.message;
            }
        } else if (action === "download-report-json") {
            try {
                await downloadValidationReport(
                    candidateId,
                    "json"
                );

                authoringElements.generationStatus.textContent =
                    `Downloaded validation JSON for ${candidateId}.`;
            } catch (error) {
                authoringElements.generationStatus.textContent =
                    error.message;
            }
        } else if (action === "download-candidate-json") {
            try {
                await downloadCandidateBundle(
                    candidateId
                );

                authoringElements.generationStatus.textContent =
                    `Downloaded candidate JSON for ${candidateId}.`;
            } catch (error) {
                authoringElements.generationStatus.textContent =
                    error.message;
            }
        }
    }
);

authoringElements.published.addEventListener(
    "click",
    async (event) => {
        const button = event.target.closest(
            "[data-unpublish-exercise]"
        );

        if (!button || authoringState.busy) {
            return;
        }

        await unpublishExercise(
            button.dataset.unpublishExercise,
            button.dataset.aiGenerated === "true"
        );
    }
);
