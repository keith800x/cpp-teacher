(() => {
    "use strict";

    const state = {
        exerciseId: "",
        timeline: null,
        loading: null,
        scheduled: false,
        enhancing: false,
    };

    function text(id) {
        const element = document.getElementById(id);
        return element ? element.textContent.trim() : "";
    }

    function isRaiiExercise() {
        return text("exerciseTopicBadge")
            .toLowerCase()
            .includes("raii");
    }

    function isReferenceSolutionView() {
        return text("visualizationExerciseTitle")
            .includes("Reference Solution");
    }

    function timelineRequestUrls(exerciseId) {
        const encoded = encodeURIComponent(exerciseId);

        if (isReferenceSolutionView()) {
            const urls = [];

            if (exerciseId.startsWith("ai_")) {
                urls.push(
                    `/api/authoring/candidates/${encoded}/reference-visualization`
                );
            }

            urls.push(
                `/api/exercises/${encoded}/solution/visualization`
            );

            return urls;
        }

        return [
            `/api/exercises/${encoded}/attempts/latest/visualization`,
        ];
    }

    async function fetchTimeline(urls) {
        for (const url of urls) {
            try {
                const response = await fetch(
                    url,
                    { cache: "no-store" }
                );

                if (!response.ok) {
                    continue;
                }

                const payload = await response.json();

                if (
                    payload &&
                    payload.timeline &&
                    Array.isArray(payload.timeline.timeline)
                ) {
                    return payload.timeline;
                }

                if (
                    payload &&
                    Array.isArray(payload.timeline)
                ) {
                    return {
                        timeline: payload.timeline,
                    };
                }
            } catch (error) {
                console.warn(
                    "RAII visualization timeline request failed:",
                    url,
                    error
                );
            }
        }

        return null;
    }

    async function loadTimeline() {
        if (!isRaiiExercise()) {
            return null;
        }

        const exerciseId = text("exerciseId");

        if (!exerciseId || exerciseId === "—") {
            return null;
        }

        const mode = isReferenceSolutionView()
            ? "reference"
            : "attempt";

        const key = `${exerciseId}:${mode}`;

        if (state.exerciseId === key && state.timeline) {
            return state.timeline;
        }

        if (state.exerciseId === key && state.loading) {
            return state.loading;
        }

        state.exerciseId = key;
        state.timeline = null;
        state.loading = fetchTimeline(
            timelineRequestUrls(exerciseId)
        )
            .then((timeline) => {
                state.timeline = timeline;
                return timeline;
            })
            .finally(() => {
                state.loading = null;
            });

        return state.loading;
    }

    function frames(documentData) {
        return (
            documentData &&
            Array.isArray(documentData.timeline)
        )
            ? documentData.timeline
            : [];
    }

    function displayedTimelineMatches(
        documentData
    ) {
        const list = frames(
            documentData
        );

        const displayedTotal =
            Number.parseInt(
                text("totalSteps"),
                10
            );

        return (
            list.length > 0 &&
            Number.isFinite(
                displayedTotal
            ) &&
            displayedTotal ===
                list.length
        );
    }

    function currentFrameIndex(documentData) {
        const list = frames(documentData);
        const step = Number.parseInt(
            text("currentStep"),
            10
        );

        if (!Number.isFinite(step) || list.length === 0) {
            return -1;
        }

        return Math.min(
            Math.max(step - 1, 0),
            list.length - 1
        );
    }

    function currentFrame(documentData) {
        const list = frames(documentData);
        const step = Number.parseInt(
            text("currentStep"),
            10
        );

        if (!Number.isFinite(step) || list.length === 0) {
            return null;
        }

        const index = Math.min(
            Math.max(step - 1, 0),
            list.length - 1
        );

        return list[index];
    }

    function heapState(frame) {
        const result = new Map();

        for (const item of Array.isArray(frame?.heap) ? frame.heap : []) {
            if (item && typeof item.id === "string") {
                result.set(
                    item.id,
                    item.alive !== false
                );
            }
        }

        return result;
    }

    function findObjectCard(name) {
        return [
            ...document.querySelectorAll(
                "#stackObjects .memory-object"
            ),
        ].find((card) => {
            const label = card.querySelector(
                ".object-name"
            );

            return (
                label &&
                label.textContent.trim() === name
            );
        }) || null;
    }

    function findFieldRow(card, fieldName) {
        if (!card) {
            return null;
        }

        return [
            ...card.querySelectorAll(".field-row"),
        ].find((row) => {
            const label = row.querySelector(
                ".field-name"
            );

            return (
                label &&
                label.textContent.trim() === fieldName
            );
        }) || null;
    }

    function setValueText(element, value) {
        if (!element) {
            return;
        }

        const dot = element.querySelector(
            ".pointer-dot"
        );

        if (
            element.textContent.trim() === value &&
            (!dot || dot.style.display === "none")
        ) {
            return;
        }

        element.textContent = "";

        if (dot) {
            dot.style.display = "none";
            element.appendChild(dot);
        }

        element.appendChild(
            document.createTextNode(value)
        );
    }

    function addAutomaticObjectNote(card) {
        if (!card || card.querySelector(".raii-object-note")) {
            return;
        }

        const note = document.createElement("div");
        note.className = "raii-object-note";
        note.textContent = (
            "automatic object — no managed heap resource is visualized"
        );

        card.appendChild(note);
    }

    function enhanceObject(card, object, heap) {
        if (!card || !object || !object.fields) {
            return;
        }

        const scopeLabel = card.querySelector(
            ".object-scope"
        );

        if (
            scopeLabel &&
            typeof object.scope === "string" &&
            object.scope
        ) {
            scopeLabel.textContent =
                `enclosing function: ${object.scope}`;
        }

        const entries = Object.entries(object.fields);

        if (entries.length === 0) {
            const fields = card.querySelector(
                ".fields"
            );

            if (fields) {
                fields.replaceChildren();
                fields.style.display = "none";
            }

            addAutomaticObjectNote(
                card
            );

            return;
        }

        const managed = entries.filter(
            ([, field]) => (
                field &&
                typeof field.points_to === "string" &&
                heap.has(field.points_to)
            )
        );

        if (managed.length > 0) {
            card.classList.add("raii-resource-manager");

            for (const [fieldName, field] of managed) {
                const row = findFieldRow(
                    card,
                    fieldName
                );

                if (!row) {
                    continue;
                }

                row.classList.add("raii-managed-row");
                row.title = (
                    "Conceptual managed-resource relationship; " +
                    "this label does not claim a literal raw-pointer " +
                    "member exists in the learner's C++."
                );

                const label = row.querySelector(
                    ".field-name"
                );

                if (
                    label &&
                    label.textContent.trim() !== "manages"
                ) {
                    label.textContent = "manages";
                }

                const value = row.querySelector(
                    ".pointer-value"
                );

                if (value) {
                    value.classList.add(
                        "raii-managed-value"
                    );

                    const alive = heap.get(
                        field.points_to
                    );

                    setValueText(
                        value,
                        alive
                            ? field.points_to
                            : `${field.points_to} (released)`
                    );
                }
            }

            return;
        }

        if (
            entries.length === 1 &&
            entries[0][0] === "data_" &&
            entries[0][1] &&
            entries[0][1].points_to == null
        ) {
            const fields = card.querySelector(".fields");

            if (fields) {
                fields.replaceChildren();
                fields.style.display = "none";
            }

            addAutomaticObjectNote(card);
        }
    }

    function hidePointerArrowLayer() {
        for (const layer of document.querySelectorAll(
            ".memory-stage .arrow-layer"
        )) {
            if (layer.style.display !== "none") {
                layer.style.display = "none";
            }

            if (layer.getAttribute("aria-hidden") !== "true") {
                layer.setAttribute("aria-hidden", "true");
            }
        }
    }

    function setElementText(id, value) {
        const element = document.getElementById(id);

        if (
            element &&
            element.textContent !== value
        ) {
            element.textContent = value;
        }
    }

    function enhanceEventCard(frame) {
        const cause = frame?.cause || {};
        const type = String(cause.type || "");
        const subject = String(cause.subject || "").trim();
        const detail = String(cause.detail || "").trim();

        if (type === "ALLOCATE_RESOURCE") {
            setElementText("eventType", "RESOURCE_ACQUIRED");
            setElementText("eventSubject", subject);
            return;
        }

        if (type === "BIND_POINTER") {
            const dot = subject.indexOf(".");
            const manager = dot > 0
                ? subject.slice(0, dot)
                : subject;

            setElementText("eventType", "MANAGES_RESOURCE");
            setElementText("eventSubject", manager);
            setElementText(
                "eventDetail",
                `manages ${detail}`
            );
            return;
        }

        if (type === "FREE_RESOURCE") {
            setElementText("eventType", "RESOURCE_RELEASED");
            setElementText("eventSubject", subject);
            return;
        }

        if (type === "DESTROY_BEGIN") {
            setElementText("eventType", "DESTRUCTOR_BEGINS");
            return;
        }

        if (type === "DESTROY_END") {
            setElementText("eventType", "OBJECT_DESTROYED");
            return;
        }
    }

    function setTeaching(title, body) {
        setElementText(
            "teachingTitle",
            title
        );

        setElementText(
            "teachingText",
            body
        );
    }

    function detailValue(detail, key) {
        const source = String(detail || "");
        const prefix = `${key}=`;
        const start = source.indexOf(prefix);

        if (start < 0) {
            return "";
        }

        const valueStart = start + prefix.length;
        const end = source.indexOf("|", valueStart);

        return (
            end < 0
                ? source.slice(valueStart)
                : source.slice(valueStart, end)
        ).trim();
    }

    function managerForResource(frame, resourceId) {
        for (const object of Array.isArray(frame?.stack)
            ? frame.stack
            : []) {
            if (!object || !object.fields) {
                continue;
            }

            for (const field of Object.values(object.fields)) {
                if (
                    field &&
                    field.points_to === resourceId
                ) {
                    return object.name || "";
                }
            }
        }

        return "";
    }

    function nextManagerForResource(
        documentData,
        frameIndex,
        resourceId
    ) {
        const list = frames(documentData);

        for (
            let index = frameIndex + 1;
            index < list.length;
            index += 1
        ) {
            const cause = list[index]?.cause || {};

            if (
                cause.type === "BIND_POINTER" &&
                String(cause.detail || "").trim() === resourceId
            ) {
                const subject = String(
                    cause.subject || ""
                );

                const dot = subject.indexOf(".");

                return dot > 0
                    ? subject.slice(0, dot)
                    : subject;
            }

            if (
                cause.type === "FREE_RESOURCE" &&
                cause.subject === resourceId
            ) {
                break;
            }
        }

        return "";
    }

    function learnerOperationName(
        documentData
    ) {
        const value =
            documentData?.raii_learner_operation;

        return (
            typeof value === "string"
                ? value.trim()
                : ""
        );
    }

    function teachRaiiFrame(
        documentData,
        frameIndex,
        frame
    ) {
        const cause = frame?.cause || {};
        const type = String(cause.type || "");
        const subject = String(cause.subject || "").trim();
        const detail = String(cause.detail || "");

        const learnerOperation =
            learnerOperationName(
                documentData
            );

        if (type === "ENTER_SCOPE") {
            const isLearnerOperation =
                subject === learnerOperation;

            setTeaching(
                isLearnerOperation
                    ? "Function lifetime begins"
                    : "Operation begins",
                isLearnerOperation
                    ? `${subject} begins. Automatic objects created in its lexical scopes will clean themselves up when those scopes end.`
                    : `${subject} begins. This function call does not by itself end the lifetime of automatic objects owned by the caller's surrounding scope.`
            );
            return;
        }

        if (type === "EXIT_SCOPE") {
            const isLearnerOperation =
                subject === learnerOperation;

            setTeaching(
                isLearnerOperation
                    ? "Function lifetime ends"
                    : "Operation completes",
                isLearnerOperation
                    ? `${subject} has finished after its automatic objects completed their required cleanup.`
                    : `${subject} returned. If the caller's lexical block ends next, any RAII cleanup caused by that block appears as separate destructor and resource-release events.`
            );
            return;
        }

        if (type === "CREATE_OBJECT") {
            const objectType = detailValue(
                detail,
                "type"
            );

            setTeaching(
                "Automatic object created",
                `${subject}${objectType ? ` (${objectType})` : ""} now has automatic storage duration. Its destructor will run automatically when its lexical lifetime ends.`
            );
            return;
        }

        if (type === "ALLOCATE_RESOURCE") {
            const manager = nextManagerForResource(
                documentData,
                frameIndex,
                subject
            );

            setTeaching(
                "Resource acquired",
                manager
                    ? `${subject} is acquired for ${manager}. The RAII object's lifetime determines when this managed resource will be released.`
                    : `${subject} is now alive. A following RAII relationship shows which automatic object manages its cleanup.`
            );
            return;
        }

        if (type === "BIND_POINTER") {
            const target = detail.trim();
            const dot = subject.indexOf(".");
            const manager = dot > 0
                ? subject.slice(0, dot)
                : subject;

            setTeaching(
                "Managed-resource relationship",
                `${manager} now manages ${target}. This visualization relationship represents RAII ownership/cleanup responsibility; it is not teaching a literal learner-visible raw-pointer field.`
            );
            return;
        }

        if (type === "DESTROY_BEGIN") {
            setTeaching(
                "Destructor begins",
                `${subject}'s lexical lifetime has ended, so its destructor starts automatically. Any resource it manages should be released as part of this deterministic cleanup.`
            );
            return;
        }

        if (type === "FREE_RESOURCE") {
            const manager = managerForResource(
                frame,
                subject
            );

            setTeaching(
                "Managed resource released",
                manager
                    ? `${manager} releases ${subject} during destructor-driven cleanup. The resource is no longer alive after this event.`
                    : `${subject} is released during deterministic cleanup and is no longer alive.`
            );
            return;
        }

        if (type === "DESTROY_END") {
            setTeaching(
                "Object lifetime ends",
                `${subject}'s destructor has finished. The automatic object is now destroyed, and any resource released during its destructor remains unavailable.`
            );
            return;
        }
    }

    async function enhance() {
        if (state.enhancing || !isRaiiExercise()) {
            return;
        }

        state.enhancing = true;

        try {
            const documentData = await loadTimeline();
            if (
                !displayedTimelineMatches(
                    documentData
                )
            ) {
                setTeaching(
                    "Visualization refresh required",
                    (
                        "This tab still has an older unfiltered RAII timeline " +
                        "in memory. Reload or reopen the visualization so the " +
                        "event card, snapshot counter, and RAII teaching panel " +
                        "all use the same cleaned timeline."
                    )
                );

                return;
            }

            const frameIndex = currentFrameIndex(
                documentData
            );
            const frame = currentFrame(documentData);

            if (!frame || frameIndex < 0) {
                return;
            }

            hidePointerArrowLayer();

            const heap = heapState(frame);

            for (const object of Array.isArray(frame.stack)
                ? frame.stack
                : []) {
                if (!object || typeof object.name !== "string") {
                    continue;
                }

                enhanceObject(
                    findObjectCard(object.name),
                    object,
                    heap
                );
            }

            enhanceEventCard(frame);

            teachRaiiFrame(
                documentData,
                frameIndex,
                frame
            );
        } finally {
            state.enhancing = false;
        }
    }

    function scheduleEnhance() {
        if (state.scheduled) {
            return;
        }

        state.scheduled = true;

        window.requestAnimationFrame(() => {
            state.scheduled = false;
            enhance().catch((error) => {
                console.warn(
                    "RAII visualization enhancement failed:",
                    error
                );
            });
        });
    }

    document.addEventListener(
        "DOMContentLoaded",
        () => {
            scheduleEnhance();

            const root = document.getElementById(
                "visualizerApp"
            );

            if (root) {
                const observer = new MutationObserver(
                    scheduleEnhance
                );

                observer.observe(
                    root,
                    {
                        childList: true,
                        subtree: true,
                        characterData: true,
                    }
                );
            }
        }
    );
})();
