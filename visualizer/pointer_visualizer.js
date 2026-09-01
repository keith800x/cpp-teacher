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

    function setText(id, value) {
        const element = document.getElementById(id);
        if (element && element.textContent !== value) {
            element.textContent = value;
        }
    }

    function detailValue(detail, key) {
        const source = String(detail || "");
        const prefix = `${key}=`;
        const start = source.indexOf(prefix);
        if (start < 0) return "";
        const valueStart = start + prefix.length;
        const end = source.indexOf("|", valueStart);
        return (end < 0 ? source.slice(valueStart) : source.slice(valueStart, end)).trim();
    }

    function objectValueMetadata(detail) {
        const raw = detailValue(detail, "value");
        if (!raw) return null;
        const equals = raw.indexOf("=");
        if (equals > 0) {
            return {
                field: raw.slice(0, equals).trim(),
                value: raw.slice(equals + 1).trim(),
            };
        }
        return { field: "state", value: raw };
    }

    function pointerField(detail) {
        return detailValue(detail, "pointer");
    }

    function timelineFrames(documentData) {
        return documentData && Array.isArray(documentData.timeline) ? documentData.timeline : [];
    }

    function isPointersExercise() {
        const topic = text("exerciseTopicBadge")
            .toLowerCase();

        return topic.includes("pointer");
    }

    function isPointerTimeline(documentData) {
        return (
            isPointersExercise() &&
            timelineFrames(documentData).some(
                (frame) =>
                    frame?.cause?.type === "BIND_POINTER"
            )
        );
    }

    function isReferenceSolutionView() {
        return text("visualizationExerciseTitle").includes(
            "Reference Solution"
        );
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

    async function fetchTimelineFrom(urls) {
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
                    Array.isArray(
                        payload.timeline.timeline
                    )
                ) {
                    return payload.timeline;
                }

                if (
                    payload &&
                    Array.isArray(
                        payload.timeline
                    )
                ) {
                    return {
                        timeline: payload.timeline,
                    };
                }
            } catch (error) {
                console.warn(
                    "Pointer visualization timeline request failed:",
                    url,
                    error
                );
            }
        }

        return null;
    }

    async function loadTimeline() {
        const exerciseId = text("exerciseId");

        if (!exerciseId || exerciseId === "—") {
            return null;
        }

        const mode = (
            isReferenceSolutionView()
                ? "reference"
                : "attempt"
        );

        const cacheKey = `${exerciseId}:${mode}`;

        if (
            state.exerciseId === cacheKey &&
            state.timeline
        ) {
            return state.timeline;
        }

        if (
            state.exerciseId === cacheKey &&
            state.loading
        ) {
            return state.loading;
        }

        state.exerciseId = cacheKey;
        state.timeline = null;

        state.loading = fetchTimelineFrom(
            timelineRequestUrls(
                exerciseId
            )
        )
            .then((data) => {
                state.timeline = data;
                return data;
            })
            .finally(() => {
                state.loading = null;
            });

        return state.loading;
    }

    function currentFrameIndex(documentData) {
        const frames = timelineFrames(documentData);
        const visibleStep = Number.parseInt(text("currentStep"), 10);
        if (!Number.isFinite(visibleStep)) return -1;
        return Math.min(Math.max(visibleStep - 1, 0), Math.max(frames.length - 1, 0));
    }

    function objectValuesThrough(documentData, index) {
        const values = new Map();
        const frames = timelineFrames(documentData);
        for (let i = 0; i <= index && i < frames.length; i += 1) {
            const cause = frames[i]?.cause || {};
            const subject = String(cause.subject || "").trim();
            if (cause.type === "CREATE_OBJECT" && subject) {
                const metadata = objectValueMetadata(cause.detail);
                if (metadata) values.set(subject, metadata);
            }
            if (
                cause.type === "WRITE_VALUE" &&
                subject &&
                !detailValue(cause.detail, "through") &&
                !detailValue(cause.detail, "via_pointer")
            ) {
                const metadata = objectValueMetadata(cause.detail);
                if (metadata) values.set(subject, metadata);
            }
        }
        return values;
    }

    function findObjectCard(name) {
        return [...document.querySelectorAll("#stackObjects .memory-object")].find((element) => {
            const objectName = element.querySelector(".object-name");
            return objectName && objectName.textContent.trim() === name;
        }) || null;
    }

    function findPointerRow(objectCard, fieldName) {
        if (!objectCard) return null;
        return [...objectCard.querySelectorAll(".field-row")].find((row) => {
            const name = row.querySelector(".field-name");
            return name && name.textContent.trim() === fieldName;
        }) || null;
    }

    function removeFakeDefaultPointerRow(objectCard) {
        if (!objectCard) return;
        for (const row of objectCard.querySelectorAll(".field-row")) {
            const fieldName = row.querySelector(".field-name");
            const pointerValue = row.querySelector(".pointer-value");
            if (
                fieldName &&
                pointerValue &&
                fieldName.textContent.trim() === "data_" &&
                pointerValue.textContent.trim().includes("nullptr")
            ) {
                row.remove();
            }
        }
    }

    function renderObjectValue(objectCard, metadata) {
        if (!objectCard || !metadata) return;
        removeFakeDefaultPointerRow(objectCard);
        let fields = objectCard.querySelector(".fields");
        if (!fields) {
            fields = document.createElement("div");
            fields.className = "fields";
            objectCard.appendChild(fields);
        }
        let row = fields.querySelector('[data-stack-object-value="true"]');
        if (!row) {
            row = document.createElement("div");
            row.className = "field-row stack-object-value-row";
            row.dataset.stackObjectValue = "true";
            const field = document.createElement("span");
            field.className = "field-name";
            field.dataset.role = "field";
            const value = document.createElement("span");
            value.className = "object-value";
            value.dataset.role = "value";
            row.append(field, value);
            fields.appendChild(row);
        }
        const field = row.querySelector('[data-role="field"]');
        const value = row.querySelector('[data-role="value"]');
        if (field) field.textContent = metadata.field;
        if (value) value.textContent = metadata.value;
    }

    function stackObjectNames(frame) {
        return new Set(
            Array.isArray(frame?.stack)
                ? frame.stack.filter((item) => item && typeof item.name === "string").map((item) => item.name)
                : []
        );
    }

    function pointerTargetInFrame(
        frame,
        subject
    ) {
        const separator = subject.indexOf(".");

        if (separator <= 0) {
            return "";
        }

        const holderName = subject.slice(
            0,
            separator
        );

        const fieldName = subject.slice(
            separator + 1
        );

        const objects = Array.isArray(
            frame?.stack
        )
            ? frame.stack
            : [];

        const holder = objects.find(
            (object) => {
                return (
                    object &&
                    object.name === holderName
                );
            }
        );

        const field = (
            holder &&
            holder.fields &&
            typeof holder.fields === "object"
        )
            ? holder.fields[fieldName]
            : null;

        return (
            field &&
            typeof field.points_to === "string"
        )
            ? field.points_to.trim()
            : "";
    }

    function previousPointerTarget(
        documentData,
        index,
        subject
    ) {
        const frames = timelineFrames(
            documentData
        );

        const holderName = subject.split(
            ".",
            1
        )[0];

        for (
            let frameIndex = index - 1;
            frameIndex >= 0;
            frameIndex -= 1
        ) {
            const frame = frames[
                frameIndex
            ];

            const target = pointerTargetInFrame(
                frame,
                subject
            );

            const hasHolder = (
                Array.isArray(
                    frame?.stack
                ) &&
                frame.stack.some(
                    (object) => {
                        return (
                            object &&
                            object.name === holderName
                        );
                    }
                )
            );

            if (
                target ||
                hasHolder
            ) {
                return target;
            }
        }

        return "";
    }

    function framePointerBindings(frame) {
        const objects = Array.isArray(frame?.stack)
            ? frame.stack
            : [];
        const bindings = [];

        for (const object of objects) {
            if (
                !object ||
                typeof object.name !== "string" ||
                !object.fields ||
                typeof object.fields !== "object"
            ) {
                continue;
            }

            for (const [fieldName, field] of Object.entries(object.fields)) {
                const target = (
                    field &&
                    typeof field.points_to === "string"
                )
                    ? field.points_to.trim()
                    : "";

                if (target) {
                    bindings.push({
                        holder: object.name,
                        field: fieldName,
                        target,
                    });
                }
            }
        }

        return bindings;
    }

    function heapResourceIds(frame) {
        return new Set(
            Array.isArray(frame?.heap)
                ? frame.heap
                    .filter(
                        (item) =>
                            item &&
                            typeof item.id === "string"
                    )
                    .map(
                        (item) =>
                            item.id.trim()
                    )
                : []
        );
    }

    function pointerName(binding) {
        return `${binding.holder}.${binding.field}`;
    }

    function naturalList(values) {
        if (values.length === 0) return "";
        if (values.length === 1) return values[0];
        if (values.length === 2) {
            return `${values[0]} and ${values[1]}`;
        }

        return (
            `${values.slice(0, -1).join(", ")}, ` +
            `and ${values[values.length - 1]}`
        );
    }

    function pointerTargetKind(frame, target) {
        if (stackObjectNames(frame).has(target)) {
            return "stack";
        }

        if (heapResourceIds(frame).has(target)) {
            return "heap";
        }

        return "unknown";
    }

    function clearStackPointerArrows() {
        document.querySelectorAll("#arrowLayer .stack-pointer-enhancement").forEach((element) => element.remove());
    }

    function drawStackPointerArrow(binding) {
        const stage = document.getElementById("memoryStage");
        const layer = document.getElementById("arrowLayer");
        const holder = findObjectCard(binding.holder);
        const target = findObjectCard(binding.target);
        const row = findPointerRow(holder, binding.field);
        if (!stage || !layer || !holder || !target || !row) return;

        const pointerValue = row.querySelector(".pointer-value") || row;
        const stageRect = stage.getBoundingClientRect();
        const sourceRect = pointerValue.getBoundingClientRect();
        const targetHeader = target.querySelector(".object-header") || target;
        const targetRect = targetHeader.getBoundingClientRect();
        const x1 = sourceRect.right - stageRect.left;
        const y1 = sourceRect.top + sourceRect.height / 2 - stageRect.top;
        const x2 = targetRect.right - stageRect.left - 10;
        const y2 = targetRect.top + targetRect.height / 2 - stageRect.top;
        const bendX = Math.min(stageRect.width / 2 - 12, Math.max(x1, x2) + 56);

        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", `M ${x1} ${y1} C ${bendX} ${y1}, ${bendX} ${y2}, ${x2} ${y2}`);
        path.setAttribute("class", "pointer-arrow stack-pointer-enhancement");
        path.setAttribute("marker-end", "url(#arrowHead)");
        layer.appendChild(path);
    }

    function teachPointerFrame(
        documentData,
        index,
        frame,
        bindings
    ) {
        const cause = frame?.cause || {};
        const subject = String(cause.subject || "").trim();
        const detail = String(cause.detail || "");
        const heapIds = heapResourceIds(frame);

        if (cause.type === "CREATE_OBJECT") {
            const field = pointerField(detail);
            const metadata = objectValueMetadata(detail);

            if (field) {
                setText("teachingTitle", "Pointer holder created");
                setText(
                    "teachingText",
                    `${subject}.${field} is a raw pointer field on a stack object. Its pointee will be shown as the timeline advances.`
                );
                return;
            }

            if (metadata) {
                setText("teachingTitle", "Stack pointee created");
                setText(
                    "teachingText",
                    `${subject} is an existing stack object with ${metadata.field} = ${metadata.value}. A non-owning pointer can observe this object without moving it to the heap.`
                );
                return;
            }

            setText("teachingTitle", "Stack object created");
            setText(
                "teachingText",
                `${subject} now exists as a stack object.`
            );
            return;
        }

        if (cause.type === "SET_NULL") {
            const previousTarget = previousPointerTarget(
                documentData,
                index,
                subject
            );

            if (previousTarget) {
                setText("teachingTitle", "Pointer cleared");

                if (
                    pointerTargetKind(frame, previousTarget) === "heap"
                ) {
                    setText(
                        "teachingText",
                        `${subject} no longer points to ${previousTarget}. Clearing this non-owning pointer does not free that heap resource; resource lifetime is handled separately.`
                    );
                } else {
                    setText(
                        "teachingText",
                        `${subject} no longer points to ${previousTarget}. The pointee can remain alive; clearing only removes this non-owning pointer relationship.`
                    );
                }

                return;
            }

            setText("teachingTitle", "Null pointer state");
            setText(
                "teachingText",
                `${subject} currently points to nothing. Checking for nullptr before dereferencing keeps this state safe.`
            );
            return;
        }

        if (cause.type === "BIND_POINTER") {
            const target = detail.trim();
            const previousTarget = previousPointerTarget(
                documentData,
                index,
                subject
            );

            const targetKind = pointerTargetKind(frame, target);

            if (
                previousTarget &&
                previousTarget !== target
            ) {
                const previousKind = pointerTargetKind(
                    frame,
                    previousTarget
                );

                setText("teachingTitle", "Pointer reseated");

                if (
                    previousKind === "heap" &&
                    targetKind === "heap"
                ) {
                    setText(
                        "teachingText",
                        `${subject} previously pointed to ${previousTarget} and now points to ${target}. Both heap resources are still alive at this point; only the non-owning pointer's target changed.`
                    );
                } else if (
                    previousKind === "stack" &&
                    targetKind === "stack"
                ) {
                    setText(
                        "teachingText",
                        `${subject} previously pointed to ${previousTarget} and now points to ${target}. Both stack objects remain alive; only the non-owning pointer's target changed.`
                    );
                } else {
                    setText(
                        "teachingText",
                        `${subject} previously pointed to ${previousTarget} and now points to ${target}. Only the non-owning pointer's target changed; pointee lifetime remains a separate concern.`
                    );
                }

                return;
            }

            if (targetKind === "stack") {
                setText("teachingTitle", "Pointer binding");
                setText(
                    "teachingText",
                    `${subject} now points to the existing stack object ${target}. This is a non-owning stack-to-stack relationship; the heap remains unchanged.`
                );
                return;
            }

            if (targetKind === "heap") {
                setText("teachingTitle", "Pointer binding");
                setText(
                    "teachingText",
                    `${subject} now points to heap resource ${target}. The raw pointer is non-owning: it observes the resource, while allocation and cleanup remain separate lifetime responsibilities.`
                );
                return;
            }

            setText("teachingTitle", "Pointer binding");
            setText(
                "teachingText",
                `${subject} now points to ${target}.`
            );
            return;
        }

        if (
            cause.type === "WRITE_VALUE" &&
            stackObjectNames(frame).has(subject)
        ) {
            const metadata = objectValueMetadata(detail);
            const incoming = bindings.filter(
                (binding) =>
                    binding.target === subject
            );

            setText("teachingTitle", "Pointee value changes");

            if (
                metadata &&
                incoming.length > 0
            ) {
                setText(
                    "teachingText",
                    `${subject}.${metadata.field} changed to ${metadata.value}, while ${naturalList(incoming.map(pointerName))} still points to the same object. Reading through the pointer observes the updated state.`
                );
            } else if (metadata) {
                setText(
                    "teachingText",
                    `${subject}.${metadata.field} changed to ${metadata.value}.`
                );
            }

            return;
        }

        if (
            cause.type === "WRITE_VALUE" &&
            heapIds.has(subject)
        ) {
            const through = (
                detailValue(detail, "through") ||
                detailValue(detail, "via_pointer")
            ).trim();

            const value = detailValue(detail, "value");

            const incoming = bindings.filter(
                (binding) =>
                    binding.target === subject
            );

            const incomingNames =
                incoming.map(pointerName);

            if (through) {
                const otherNames =
                    incomingNames.filter(
                        (name) =>
                            name !== through
                    );

                setText(
                    "teachingTitle",
                    "Write through pointer"
                );

                if (otherNames.length > 0) {
                    setText(
                        "teachingText",
                        `${through} points to ${subject}. Writing through this raw pointer changes the pointee${value ? ` to ${value}` : ""}. ${naturalList(otherNames)} also points to ${subject}, so it observes the same updated resource.`
                    );
                } else {
                    setText(
                        "teachingText",
                        `${through} points to ${subject}. Writing through this raw pointer changes the pointee${value ? ` to ${value}` : ""}; the pointer still refers to that same resource.`
                    );
                }

                return;
            }

            setText(
                "teachingTitle",
                "Pointee value changes"
            );

            if (incomingNames.length > 0) {
                setText(
                    "teachingText",
                    `${subject} changed${value ? ` to ${value}` : ""}. ${naturalList(incomingNames)} still points to this heap resource and therefore observes its updated state.`
                );
            } else {
                setText(
                    "teachingText",
                    `${subject} changed${value ? ` to ${value}` : ""}.`
                );
            }

            return;
        }

        if (cause.type === "FREE_RESOURCE") {
            const incoming = bindings.filter(
                (binding) =>
                    binding.target === subject
            );

            const incomingNames =
                incoming.map(pointerName);

            setText(
                "teachingTitle",
                "Pointee lifetime ends"
            );

            if (incomingNames.length > 0) {
                setText(
                    "teachingText",
                    `${subject} has been freed. ${naturalList(incomingNames)} still stores this target and is now dangling; do not dereference it until the pointer is cleared or reseated.`
                );
            } else {
                setText(
                    "teachingText",
                    `${subject} has been freed. No tracked pointer still points to it, so no tracked dangling relationship remains.`
                );
            }

            return;
        }
    }

    async function enhance() {
        if (state.enhancing) return;
        state.enhancing = true;
        try {
            const documentData = await loadTimeline();
            if (!documentData || !isPointerTimeline(documentData)) {
                clearStackPointerArrows();
                return;
            }
            const index = currentFrameIndex(documentData);
            const frames = timelineFrames(documentData);
            if (index < 0 || !frames[index]) return;

            const values = objectValuesThrough(documentData, index);
            for (const [name, metadata] of values) {
                renderObjectValue(findObjectCard(name), metadata);
            }

            clearStackPointerArrows();
            const bindings = framePointerBindings(frames[index]);
            for (const binding of bindings) drawStackPointerArrow(binding);
            teachPointerFrame(
                documentData,
                index,
                frames[index],
                bindings
            );
        } finally {
            state.enhancing = false;
        }
    }

    function scheduleEnhancement() {
        if (state.scheduled) return;
        state.scheduled = true;
        window.requestAnimationFrame(() => {
            state.scheduled = false;
            void enhance();
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        const app = document.getElementById("visualizerApp");
        if (!app) return;
        const observer = new MutationObserver(scheduleEnhancement);
        observer.observe(app, { subtree: true, childList: true, characterData: true });
        window.addEventListener("resize", scheduleEnhancement);
        scheduleEnhancement();
    });
})();
