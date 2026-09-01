(() => {
    "use strict";

    const BUTTON_IDS = [
        "downloadVisualizationDataButton",
        "downloadVisualizationSnapshotButton",
        "downloadVisualizationAllButton",
    ];

    function byId(id) {
        return document.getElementById(id);
    }

    function text(id) {
        const element = byId(id);
        return element ? element.textContent.trim() : "";
    }

    function isReferenceSolutionView() {
        return text("visualizationExerciseTitle").includes(
            "Reference Solution"
        );
    }

    function visualizationMode() {
        return isReferenceSolutionView()
            ? "reference"
            : "attempt";
    }

    function safeFilePart(value) {
        const cleaned = String(value || "visualization")
            .trim()
            .replace(/[^A-Za-z0-9._-]+/g, "-")
            .replace(/^-+|-+$/g, "");

        return cleaned || "visualization";
    }

    function exportBaseName() {
        return [
            safeFilePart(text("exerciseId")),
            visualizationMode(),
        ].join("-");
    }

    function timelineUrls(exerciseId) {
        const encoded = encodeURIComponent(exerciseId);

        if (visualizationMode() === "reference") {
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

    async function fetchTimeline() {
        const exerciseId = text("exerciseId");

        if (!exerciseId || exerciseId === "—") {
            throw new Error(
                "No visualization is currently loaded."
            );
        }

        for (const url of timelineUrls(exerciseId)) {
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
                    "Visualization export timeline request failed:",
                    url,
                    error
                );
            }
        }

        throw new Error(
            "Could not load the current visualization timeline."
        );
    }

    function downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");

        anchor.href = url;
        anchor.download = filename;
        anchor.style.display = "none";

        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();

        window.setTimeout(
            () => URL.revokeObjectURL(url),
            1000
        );
    }

    function jsonBlob(data) {
        return new Blob(
            [
                JSON.stringify(data, null, 2),
                "\n",
            ],
            {
                type: "application/json;charset=utf-8",
            }
        );
    }

    function currentStepNumber() {
        const value = Number.parseInt(
            text("currentStep"),
            10
        );

        return Number.isFinite(value)
            ? value
            : 0;
    }

    function totalStepNumber() {
        const value = Number.parseInt(
            text("totalSteps"),
            10
        );

        return Number.isFinite(value)
            ? value
            : 0;
    }

    function timelineStepCount(timeline) {
        if (
            !timeline ||
            !Array.isArray(
                timeline.timeline
            )
        ) {
            return 0;
        }

        return timeline.timeline.length;
    }

    function collectStyleText() {
        const chunks = [];

        for (const sheet of document.styleSheets) {
            try {
                if (!sheet.cssRules) {
                    continue;
                }

                for (const rule of sheet.cssRules) {
                    chunks.push(rule.cssText);
                }
            } catch (error) {
                console.warn(
                    "Skipping an unreadable stylesheet during export.",
                    error
                );
            }
        }

        return chunks.join("\n");
    }

    function cloneForExport(source) {
        const clone = source.cloneNode(true);

        clone.classList.remove("hidden");
        clone.style.margin = "0";
        clone.style.width = `${source.scrollWidth}px`;
        clone.style.maxWidth = "none";

        return clone;
    }

    function escapeXmlAttribute(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/"/g, "&quot;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    async function captureElementSvg(source) {
        if (!source) {
            throw new Error(
                "The visualizer is not visible."
            );
        }

        if (document.fonts && document.fonts.ready) {
            await document.fonts.ready;
        }

        const width = Math.ceil(source.scrollWidth);
        const height = Math.ceil(source.scrollHeight);

        if (width <= 0 || height <= 0) {
            throw new Error(
                "The visualizer has no drawable size."
            );
        }

        const clone = cloneForExport(source);
        const styleText = collectStyleText();

        const bodyStyle = window.getComputedStyle(
            document.body
        );

        const background = (
            bodyStyle.backgroundColor &&
            bodyStyle.backgroundColor !==
                "rgba(0, 0, 0, 0)"
        )
            ? bodyStyle.backgroundColor
            : "#0b1119";

        const serialized = new XMLSerializer()
            .serializeToString(clone);

        const title = [
            text("visualizationExerciseTitle"),
            `Snapshot ${currentStepNumber()}/${totalStepNumber()}`,
        ]
            .filter(Boolean)
            .join(" — ");

        const svg = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeXmlAttribute(title)}">`,
            `<title>${title.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")}</title>`,
            `<foreignObject x="0" y="0" width="100%" height="100%">`,
            `<div xmlns="http://www.w3.org/1999/xhtml" style="margin:0;padding:0;background:${escapeXmlAttribute(background)};width:${width}px;min-height:${height}px;">`,
            `<style>${styleText}</style>`,
            serialized,
            `</div>`,
            `</foreignObject>`,
            `</svg>`,
        ].join("");

        return new Blob(
            [svg],
            {
                type: "image/svg+xml;charset=utf-8",
            }
        );
    }

    function nextAnimationFrame() {
        return new Promise(
            (resolve) => {
                window.requestAnimationFrame(
                    () => resolve()
                );
            }
        );
    }

    async function settleVisualization() {
        await nextAnimationFrame();
        await nextAnimationFrame();

        await new Promise(
            (resolve) => {
                window.setTimeout(
                    resolve,
                    90
                );
            }
        );

        await nextAnimationFrame();
    }

    async function waitForStep(
        expected,
        timeoutMs = 2500
    ) {
        const start = performance.now();

        while (
            performance.now() - start < timeoutMs
        ) {
            if (
                currentStepNumber() === expected
            ) {
                await settleVisualization();
                return;
            }

            await nextAnimationFrame();
        }

        throw new Error(
            `Timed out waiting for snapshot ${expected}.`
        );
    }

    async function moveToStep(target) {
        const previous = byId("previousButton");
        const next = byId("nextButton");

        if (!previous || !next) {
            throw new Error(
                "Timeline navigation controls are unavailable."
            );
        }

        while (currentStepNumber() > target) {
            const expected =
                currentStepNumber() - 1;

            previous.click();
            await waitForStep(expected);
        }

        while (currentStepNumber() < target) {
            const expected =
                currentStepNumber() + 1;

            next.click();
            await waitForStep(expected);
        }
    }

    function crc32(bytes) {
        let crc = 0xffffffff;

        for (
            let i = 0;
            i < bytes.length;
            i += 1
        ) {
            crc ^= bytes[i];

            for (
                let bit = 0;
                bit < 8;
                bit += 1
            ) {
                crc = (
                    (crc >>> 1) ^
                    (
                        (crc & 1)
                            ? 0xedb88320
                            : 0
                    )
                );
            }
        }

        return (crc ^ 0xffffffff) >>> 0;
    }

    function dosDateTime(date = new Date()) {
        const year = Math.max(
            1980,
            date.getFullYear()
        );

        return {
            dosTime:
                (date.getHours() << 11) |
                (date.getMinutes() << 5) |
                Math.floor(date.getSeconds() / 2),
            dosDate:
                ((year - 1980) << 9) |
                ((date.getMonth() + 1) << 5) |
                date.getDate(),
        };
    }

    function uint16(value) {
        return new Uint8Array(
            [
                value & 0xff,
                (value >> 8) & 0xff,
            ]
        );
    }

    function uint32(value) {
        return new Uint8Array(
            [
                value & 0xff,
                (value >> 8) & 0xff,
                (value >> 16) & 0xff,
                (value >> 24) & 0xff,
            ]
        );
    }

    function concatBytes(chunks) {
        const total = chunks.reduce(
            (sum, chunk) => sum + chunk.length,
            0
        );

        const output = new Uint8Array(total);
        let offset = 0;

        for (const chunk of chunks) {
            output.set(chunk, offset);
            offset += chunk.length;
        }

        return output;
    }

    async function createStoredZip(files) {
        const encoder = new TextEncoder();
        const localParts = [];
        const centralParts = [];

        let localOffset = 0;

        const {
            dosTime,
            dosDate,
        } = dosDateTime();

        for (const file of files) {
            const nameBytes = encoder.encode(
                file.name
            );

            const dataBytes = new Uint8Array(
                await file.blob.arrayBuffer()
            );

            const crc = crc32(dataBytes);

            const localHeader = concatBytes(
                [
                    uint32(0x04034b50),
                    uint16(20),
                    uint16(0),
                    uint16(0),
                    uint16(dosTime),
                    uint16(dosDate),
                    uint32(crc),
                    uint32(dataBytes.length),
                    uint32(dataBytes.length),
                    uint16(nameBytes.length),
                    uint16(0),
                    nameBytes,
                ]
            );

            localParts.push(
                localHeader,
                dataBytes
            );

            centralParts.push(
                concatBytes(
                    [
                        uint32(0x02014b50),
                        uint16(20),
                        uint16(20),
                        uint16(0),
                        uint16(0),
                        uint16(dosTime),
                        uint16(dosDate),
                        uint32(crc),
                        uint32(dataBytes.length),
                        uint32(dataBytes.length),
                        uint16(nameBytes.length),
                        uint16(0),
                        uint16(0),
                        uint16(0),
                        uint16(0),
                        uint32(0),
                        uint32(localOffset),
                        nameBytes,
                    ]
                )
            );

            localOffset += (
                localHeader.length +
                dataBytes.length
            );
        }

        const central = concatBytes(centralParts);

        const end = concatBytes(
            [
                uint32(0x06054b50),
                uint16(0),
                uint16(0),
                uint16(files.length),
                uint16(files.length),
                uint32(central.length),
                uint32(localOffset),
                uint16(0),
            ]
        );

        return new Blob(
            [
                concatBytes(
                    [
                        ...localParts,
                        central,
                        end,
                    ]
                ),
            ],
            {
                type: "application/zip",
            }
        );
    }

    function timelineExportPayload(timeline) {
        return {
            export_schema_version: 1,
            exported_at:
                new Date().toISOString(),
            exercise_id:
                text("exerciseId"),
            title:
                text("visualizationExerciseTitle"),
            mode:
                visualizationMode(),
            timeline,
        };
    }

    function setButtonsBusy(
        busy,
        activeId = ""
    ) {
        for (const id of BUTTON_IDS) {
            const button = byId(id);

            if (!button) {
                continue;
            }

            if (!button.dataset.originalLabel) {
                button.dataset.originalLabel =
                    button.textContent;
            }

            button.disabled = busy;

            if (!busy) {
                button.textContent =
                    button.dataset.originalLabel;
            }
        }

        if (busy && activeId) {
            const active = byId(activeId);

            if (active) {
                active.textContent = "Exporting…";
            }
        }
    }

    async function downloadTimelineData() {
        setButtonsBusy(
            true,
            "downloadVisualizationDataButton"
        );

        try {
            const timeline = await fetchTimeline();

            downloadBlob(
                jsonBlob(
                    timelineExportPayload(
                        timeline
                    )
                ),
                `${exportBaseName()}-timeline.json`
            );
        } finally {
            setButtonsBusy(false);
        }
    }

    async function downloadCurrentSnapshotSvg() {
        setButtonsBusy(
            true,
            "downloadVisualizationSnapshotButton"
        );

        try {
            await settleVisualization();

            const blob = await captureElementSvg(
                byId("visualizerApp")
            );

            downloadBlob(
                blob,
                `${exportBaseName()}-snapshot-${String(currentStepNumber()).padStart(2, "0")}.svg`
            );
        } finally {
            setButtonsBusy(false);
        }
    }

    async function downloadAllSnapshots() {
        setButtonsBusy(
            true,
            "downloadVisualizationAllButton"
        );

        const originalStep =
            currentStepNumber();

        try {
            const timeline = await fetchTimeline();
            const total = totalStepNumber();
            const deliveredTotal =
                timelineStepCount(
                    timeline
                );

            if (total <= 0) {
                throw new Error(
                    "This visualization has no snapshots."
                );
            }

            if (
                deliveredTotal <= 0 ||
                deliveredTotal !== total
            ) {
                throw new Error(
                    (
                        "Visualization timeline changed while this view "
                        + "was open. The page shows "
                        + total
                        + " snapshot(s), but the current reference API "
                        + "delivers "
                        + deliveredTotal
                        + ". Reopen Reference Solution before exporting."
                    )
                );
            }

            const files = [
                {
                    name: "timeline.json",
                    blob: jsonBlob(
                        timelineExportPayload(
                            timeline
                        )
                    ),
                },
            ];

            await moveToStep(1);

            for (
                let step = 1;
                step <= total;
                step += 1
            ) {
                if (
                    currentStepNumber() !== step
                ) {
                    await moveToStep(step);
                }

                await settleVisualization();

                const active = byId(
                    "downloadVisualizationAllButton"
                );

                if (active) {
                    active.textContent =
                        `Export ${step}/${total}`;
                }

                const svg =
                    await captureElementSvg(
                        byId("visualizerApp")
                    );

                files.push(
                    {
                        name:
                            `snapshots/snapshot-${String(step).padStart(2, "0")}.svg`,
                        blob: svg,
                    }
                );
            }

            const archive =
                await createStoredZip(files);

            downloadBlob(
                archive,
                `${exportBaseName()}-snapshots.zip`
            );
        } finally {
            if (
                originalStep > 0 &&
                currentStepNumber() !== originalStep
            ) {
                try {
                    await moveToStep(
                        originalStep
                    );
                } catch (error) {
                    console.warn(
                        "Could not restore the original snapshot after export.",
                        error
                    );
                }
            }

            setButtonsBusy(false);
        }
    }

    function reportExportError(error) {
        console.error(
            "Visualization export failed:",
            error
        );

        window.alert(
            error && error.message
                ? error.message
                : "Visualization export failed."
        );
    }

    function wireButton(id, handler) {
        const button = byId(id);

        if (!button) {
            return;
        }

        button.addEventListener(
            "click",
            () => {
                handler().catch(
                    reportExportError
                );
            }
        );
    }

    document.addEventListener(
        "DOMContentLoaded",
        () => {
            wireButton(
                "downloadVisualizationDataButton",
                downloadTimelineData
            );

            wireButton(
                "downloadVisualizationSnapshotButton",
                downloadCurrentSnapshotSvg
            );

            wireButton(
                "downloadVisualizationAllButton",
                downloadAllSnapshots
            );
        }
    );
})();
