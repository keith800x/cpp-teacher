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
        return element
            ? element.textContent.trim()
            : "";
    }

    function setText(id, value) {
        const element = document.getElementById(id);

        if (
            element &&
            element.textContent !== value
        ) {
            element.textContent = value;
        }
    }

    function isMoveExercise() {
        return text("exerciseTopicBadge")
            .toLowerCase()
            .includes("move");
    }

    function isReferenceSolutionView() {
        return text("visualizationExerciseTitle")
            .includes("Reference Solution");
    }

    function timelineRequestUrls(exerciseId) {
        const encoded =
            encodeURIComponent(exerciseId);

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
                    {
                        cache: "no-store",
                    }
                );

                if (!response.ok) {
                    continue;
                }

                const payload =
                    await response.json();

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
                        timeline:
                            payload.timeline,
                    };
                }
            } catch (error) {
                console.warn(
                    "Move visualization timeline request failed:",
                    url,
                    error
                );
            }
        }

        return null;
    }

    async function loadTimeline() {
        if (!isMoveExercise()) {
            return null;
        }

        const exerciseId =
            text("exerciseId");

        if (
            !exerciseId ||
            exerciseId === "—"
        ) {
            return null;
        }

        const mode =
            isReferenceSolutionView()
                ? "reference"
                : "attempt";

        const displayedTotal =
            text("totalSteps");

        const key =
            `${exerciseId}:${mode}:${displayedTotal}`;

        if (
            state.exerciseId === key &&
            state.timeline
        ) {
            return state.timeline;
        }

        if (
            state.exerciseId === key &&
            state.loading
        ) {
            return state.loading;
        }

        state.exerciseId = key;
        state.timeline = null;

        state.loading = fetchTimeline(
            timelineRequestUrls(
                exerciseId
            )
        )
            .then((timeline) => {
                state.timeline =
                    timeline;

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
            Array.isArray(
                documentData.timeline
            )
        )
            ? documentData.timeline
            : [];
    }

    function displayedTimelineMatches(
        documentData
    ) {
        const list =
            frames(documentData);

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

    function currentFrameIndex(
        documentData
    ) {
        const list =
            frames(documentData);

        const step =
            Number.parseInt(
                text("currentStep"),
                10
            );

        if (
            !Number.isFinite(step) ||
            list.length === 0
        ) {
            return -1;
        }

        return Math.min(
            Math.max(
                step - 1,
                0
            ),
            list.length - 1
        );
    }

    function currentFrame(
        documentData
    ) {
        const index =
            currentFrameIndex(
                documentData
            );

        if (index < 0) {
            return null;
        }

        return frames(
            documentData
        )[index];
    }

    function detailValue(
        detail,
        key
    ) {
        const source =
            String(detail || "");

        const prefix =
            `${key}=`;

        const start =
            source.indexOf(prefix);

        if (start < 0) {
            return "";
        }

        const valueStart =
            start +
            prefix.length;

        const end =
            source.indexOf(
                "|",
                valueStart
            );

        return (
            end < 0
                ? source.slice(
                    valueStart
                )
                : source.slice(
                    valueStart,
                    end
                )
        ).trim();
    }

    function setTeaching(
        title,
        body
    ) {
        setText(
            "teachingTitle",
            title
        );

        setText(
            "teachingText",
            body
        );
    }

    function enhanceObjectCards() {
        for (const card of document.querySelectorAll(
            "#stackObjects .memory-object"
        )) {
            const fields =
                card.querySelector(
                    ".fields"
                );

            if (!fields) {
                continue;
            }

            const rows =
                fields.querySelectorAll(
                    ".field-row"
                );

            if (rows.length === 0) {
                fields.replaceChildren();

                const note =
                    document.createElement(
                        "div"
                    );

                note.className =
                    "empty-state";

                note.textContent =
                    "Member state is tracked below; no raw pointer field is implied.";

                fields.appendChild(
                    note
                );
            }
        }
    }

    function enhanceMemberStateSection() {
        const values =
            document.getElementById(
                "stackValues"
            );

        if (!values) {
            return;
        }

        const section =
            values.closest(
                ".stack-subsection"
            );

        const title =
            section
                ? section.querySelector(
                    ".subsection-title"
                )
                : null;

        if (title) {
            title.textContent =
                "Tracked member state";
        }

        for (const card of values.querySelectorAll(
            ".stack-value-card"
        )) {
            const name =
                card.querySelector(
                    ".value-name"
                );

            const type =
                card.querySelector(
                    ".value-type"
                );

            if (
                name &&
                name.textContent.trim().endsWith(
                    ".load_"
                ) &&
                type
            ) {
                type.textContent =
                    "SupplyLoad packages";
            }
        }
    }

    function hideDeadAliases() {
        for (const card of document.querySelectorAll(
            "#stackAliases .alias-card.out-of-scope"
        )) {
            card.remove();
        }
    }

    function enhanceAliasCard(frame) {
        const cause =
            frame?.cause || {};

        if (
            cause.type !== "BIND_ALIAS" ||
            cause.subject !== "other"
        ) {
            return;
        }

        const card =
            document.querySelector(
                "#stackAliases .alias-card"
            );

        if (!card) {
            return;
        }

        const badge =
            card.querySelector(
                ".alias-badge"
            );

        if (badge) {
            badge.textContent =
                "rvalue-reference parameter";
        }

        const target =
            card.querySelector(
                ".alias-target"
            );

        if (target) {
            target.textContent =
                "refers to loadingKit";
        }
    }

    function enhanceEventCard(frame) {
        const cause =
            frame?.cause || {};

        const type =
            String(
                cause.type || ""
            );

        const subject =
            String(
                cause.subject || ""
            ).trim();

        const detail =
            String(
                cause.detail || ""
            );

        if (type === "INITIALIZE_VALUE") {
            setText(
                "eventType",
                "INITIALIZE_VALUE"
            );

            setText(
                "eventDetail",
                `packages=${detailValue(
                    detail,
                    "packages"
                )}`
            );

            return;
        }

        if (type === "TRANSFER_VALUE") {
            const source =
                detailValue(
                    detail,
                    "from"
                );

            const packages =
                detailValue(
                    detail,
                    "packages"
                );

            setText(
                "eventType",
                "TRANSFER_VALUE"
            );

            setText(
                "eventSubject",
                subject
            );

            setText(
                "eventDetail",
                `receives ${packages} from ${source}`
            );

            return;
        }

        if (type === "COPY_VALUE") {
            const source =
                detailValue(
                    detail,
                    "from"
                );

            const packages =
                detailValue(
                    detail,
                    "packages"
                );

            setText(
                "eventType",
                "COPY_VALUE"
            );

            setText(
                "eventSubject",
                subject
            );

            setText(
                "eventDetail",
                `copies ${packages} from ${source}`
            );

            return;
        }

        if (type === "CLEAR_VALUE") {
            const destination =
                detailValue(
                    detail,
                    "moved_to"
                );

            setText(
                "eventType",
                "CLEAR_VALUE"
            );

            setText(
                "eventSubject",
                subject
            );

            setText(
                "eventDetail",
                `becomes 0 after move to ${destination}`
            );

            return;
        }

        if (type === "SOURCE_RETAINED") {
            const destination =
                detailValue(
                    detail,
                    "copied_to"
                );

            const packages =
                detailValue(
                    detail,
                    "packages"
                );

            setText(
                "eventType",
                "SOURCE_RETAINED"
            );

            setText(
                "eventSubject",
                subject
            );

            setText(
                "eventDetail",
                `still has ${packages} after ${destination} was created`
            );

            return;
        }

        if (
            type === "BIND_ALIAS" &&
            subject === "other"
        ) {
            setText(
                "eventType",
                "BIND_RVALUE_REFERENCE"
            );

            setText(
                "eventDetail",
                "other refers to loadingKit"
            );
        }
    }

    function teachMoveFrame(
        frame
    ) {
        const cause =
            frame?.cause || {};

        const type =
            String(
                cause.type || ""
            );

        const subject =
            String(
                cause.subject || ""
            ).trim();

        const detail =
            String(
                cause.detail || ""
            );

        if (
            type === "ENTER_SCOPE" &&
            subject === "supply-handoff"
        ) {
            setTeaching(
                "Handoff begins",
                "The source FieldKit is created first. Watch its tracked load_ state before and after the receiving kit is constructed."
            );
            return;
        }

        if (
            type === "CREATE_OBJECT" &&
            subject === "loadingKit"
        ) {
            setTeaching(
                "Source object created",
                "loadingKit is the source object that will later be passed to the move constructor."
            );
            return;
        }

        if (type === "INITIALIZE_VALUE") {
            const packages =
                detailValue(
                    detail,
                    "packages"
                );

            setTeaching(
                "Source member initialized",
                `${subject} begins with ${packages} packages. This is the state that should be handed to the destination.`
            );
            return;
        }

        if (
            type === "ENTER_SCOPE" &&
            subject === "FieldKit"
        ) {
            setTeaching(
                "Move constructor begins",
                "FieldKit(FieldKit&& other) is now constructing the destination. The rvalue-reference parameter identifies the source object."
            );
            return;
        }

        if (
            type === "BIND_ALIAS" &&
            subject === "other"
        ) {
            setTeaching(
                "Source parameter bound",
                "other is an rvalue-reference parameter referring to loadingKit. std::move itself is only a cast; the actual state transfer happens when load_ is initialized from std::move(other.load_)."
            );
            return;
        }

        if (
            type === "CREATE_OBJECT" &&
            subject === "stationKit"
        ) {
            setTeaching(
                "Destination object created",
                "stationKit is the destination FieldKit. The next state event shows whether its load_ was moved or merely copied."
            );
            return;
        }

        if (type === "TRANSFER_VALUE") {
            const source =
                detailValue(
                    detail,
                    "from"
                );

            const packages =
                detailValue(
                    detail,
                    "packages"
                );

            setTeaching(
                "Member state transferred",
                `${subject} receives ${packages} packages from ${source}. This is the successful destination side of the move.`
            );
            return;
        }

        if (type === "CLEAR_VALUE") {
            const destination =
                detailValue(
                    detail,
                    "moved_to"
                );

            setTeaching(
                "Moved-from source becomes empty",
                `${subject} is now 0 after transferring its packages to ${destination}. SupplyLoad explicitly defines this empty moved-from state.`
            );
            return;
        }

        if (type === "COPY_VALUE") {
            const source =
                detailValue(
                    detail,
                    "from"
                );

            setTeaching(
                "Member was copied",
                `${subject} received state from ${source}, but this path did not establish a move. The source should become empty in this exercise.`
            );
            return;
        }

        if (type === "SOURCE_RETAINED") {
            const packages =
                detailValue(
                    detail,
                    "packages"
                );

            setTeaching(
                "Source still has packages",
                `${subject} still reports ${packages}. That is copy-like behavior, so the handoff is incomplete.`
            );
            return;
        }

        if (
            type === "EXIT_SCOPE" &&
            subject === "FieldKit"
        ) {
            setTeaching(
                "Move constructor completes",
                "The move-constructor parameter other is now out of scope. It is no longer shown as an active alias."
            );
            return;
        }

        if (
            type === "DESTROY_BEGIN"
        ) {
            setTeaching(
                "Object cleanup begins",
                `${subject} is leaving its test scope. This cleanup happens after the move-state lesson has already been established.`
            );
            return;
        }

        if (
            type === "DESTROY_END"
        ) {
            setTeaching(
                "Object lifetime ends",
                `${subject} has been destroyed.`
            );
            return;
        }

        if (
            type === "EXIT_SCOPE" &&
            subject === "supply-handoff"
        ) {
            setTeaching(
                "Handoff complete",
                "The successful path transferred the package count to stationKit and left loadingKit empty before either object was destroyed."
            );
        }
    }

    async function enhance() {
        if (
            state.enhancing ||
            !isMoveExercise()
        ) {
            return;
        }

        state.enhancing = true;

        try {
            const documentData =
                await loadTimeline();

            if (
                !displayedTimelineMatches(
                    documentData
                )
            ) {
                setTeaching(
                    "Visualization refresh required",
                    "Reload or reopen this Move Semantics visualization so the event cards, tracked member state, and teaching panel all use the same timeline."
                );

                return;
            }

            const frame =
                currentFrame(
                    documentData
                );

            if (!frame) {
                return;
            }

            enhanceObjectCards();
            enhanceMemberStateSection();
            hideDeadAliases();
            enhanceAliasCard(frame);
            enhanceEventCard(frame);
            teachMoveFrame(frame);
        } finally {
            state.enhancing = false;
        }
    }

    function scheduleEnhance() {
        if (state.scheduled) {
            return;
        }

        state.scheduled = true;

        window.requestAnimationFrame(
            () => {
                state.scheduled = false;

                enhance().catch(
                    (error) => {
                        console.warn(
                            "Move visualization enhancement failed:",
                            error
                        );
                    }
                );
            }
        );
    }

    document.addEventListener(
        "DOMContentLoaded",
        () => {
            scheduleEnhance();

            const root =
                document.getElementById(
                    "visualizerApp"
                );

            if (root) {
                const observer =
                    new MutationObserver(
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
