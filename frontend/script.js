"use strict";

// ============================================
// DEEPTRUTH - COMPLETE FRONTEND
// ============================================

const API = window.location.origin;

const $ = id => document.getElementById(id);

let selectedPreviewURL = null;
let latestReport = null;
let promptPreviewURL = null;


// ============================================
// INITIALIZATION
// ============================================

document.addEventListener("DOMContentLoaded", () => {
    hideLoader();
    setupNavigation();
    setupFileUpload();
    setupDragAndDrop();
    setupPromptInvestigation();

    loadHistory();
    loadStatistics();

    console.log("DeepTruth is ready.");
});


// ============================================
// LOADER
// ============================================

function hideLoader() {
    const loader = $("appLoader");

    if (loader) {
        loader.style.display = "none";
        loader.remove();
    }

    const layout = $("appLayout");

    if (layout) {
        layout.style.display = "";
    }
}


// ============================================
// NAVIGATION
// ============================================

function setupNavigation() {
    document.querySelectorAll("[data-page]").forEach(button => {
        button.addEventListener("click", () => {
            openPage(button.dataset.page);
        });
    });

    document.querySelectorAll("[data-go]").forEach(button => {
        button.addEventListener("click", () => {
            openPage(button.dataset.go);
        });
    });

    const menuToggle = $("menuToggle");
    const sidebar = $("sidebar");

    if (menuToggle && sidebar) {
        menuToggle.addEventListener("click", () => {
            sidebar.classList.toggle("open");
        });
    }
}

function openPage(pageName) {
    document.querySelectorAll(".page-section").forEach(section => {
        section.classList.remove("active");
    });

    document.querySelectorAll("[data-page]").forEach(button => {
        button.classList.remove("active");
    });

    const page = $(`page-${pageName}`);

    if (page) page.classList.add("active");

    document.querySelectorAll(`[data-page="${pageName}"]`).forEach(button => {
        button.classList.add("active");
    });

    const pageTitle = $("pageTitle");

    if (pageTitle) {
        pageTitle.textContent =
            pageName.charAt(0).toUpperCase() + pageName.slice(1);
    }

    const sidebar = $("sidebar");

    if (sidebar) sidebar.classList.remove("open");
}


// ============================================
// STATUS
// ============================================

function setStatus(message, isError = false) {
    const status = $("status");

    if (!status) return;

    status.textContent = message;
    status.style.color = isError ? "#ff7070" : "";
}

function setPromptStatus(message, isError = false) {
    const status = $("promptStatus");

    if (!status) return;

    status.textContent = message;
    status.style.color = isError ? "#ff7070" : "";
}


// ============================================
// SAFE HTML
// ============================================

function safe(value) {
    return String(value ?? "").replace(
        /[&<>"']/g,
        char => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        })[char]
    );
}

function displayValue(value, fallback = "Not available") {
    if (value === undefined || value === null || value === "") {
        return fallback;
    }

    return safe(value);
}

function validPercent(value) {
    if (value === undefined || value === null || value === "") {
        return null;
    }

    const number = Number(value);

    if (!Number.isFinite(number)) return null;

    return Math.min(100, Math.max(0, number));
}

function getFirstPercent(object, keys) {
    for (const key of keys) {
        const value = validPercent(object?.[key]);

        if (value !== null) return value;
    }

    return null;
}

function formatPercent(value) {
    return value === null ? "Not available" : `${value.toFixed(1)}%`;
}


// ============================================
// FILE PREVIEW
// ============================================

function clearSelectedPreview() {
    if (selectedPreviewURL) {
        URL.revokeObjectURL(selectedPreviewURL);
        selectedPreviewURL = null;
    }
}

function setupFileUpload() {
    const input = $("mediaFile");

    if (!input) return;

    input.addEventListener("change", () => {
        const file = input.files[0];
        const fileName = $("fileName");

        clearSelectedPreview();

        if (!file) {
            if (fileName) fileName.textContent = "No file selected";
            return;
        }

        if (fileName) fileName.textContent = file.name;

        selectedPreviewURL = URL.createObjectURL(file);

        showSelectedPreview(file);
        setStatus("File selected. Ready for forensic scan.");
    });
}

function showSelectedPreview(file) {
    const parent = $("investigationInfo");

    if (!parent) return;

    let preview = $("selectedMediaPreview");

    if (!preview) {
        preview = document.createElement("div");
        preview.id = "selectedMediaPreview";
        parent.insertAdjacentElement("afterend", preview);
    }

    let mediaHTML = "";

    if (file.type.startsWith("image/")) {
        mediaHTML = `
            <img src="${safe(selectedPreviewURL)}"
                 alt="Selected image"
                 style="width:100%;max-height:350px;object-fit:contain;border-radius:12px;margin-top:12px;">
        `;
    } else if (file.type.startsWith("video/")) {
        mediaHTML = `
            <video src="${safe(selectedPreviewURL)}"
                   controls
                   style="width:100%;max-height:350px;border-radius:12px;margin-top:12px;">
            </video>
        `;
    } else {
        mediaHTML = `<p>Audio preview is not available here.</p>`;
    }

    preview.innerHTML = `
        <div class="panel" style="margin-top:20px;">
            <h3>Selected Media Preview</h3>
            <p>${safe(file.name)}</p>
            ${mediaHTML}
        </div>
    `;
}


// ============================================
// DRAG AND DROP
// ============================================

function setupDragAndDrop() {
    const dropZone = $("dropZone");
    const input = $("mediaFile");

    if (!dropZone || !input) return;

    dropZone.addEventListener("dragover", event => {
        event.preventDefault();
        dropZone.classList.add("drag-over");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("drag-over");
    });

    dropZone.addEventListener("drop", event => {
        event.preventDefault();
        dropZone.classList.remove("drag-over");

        if (event.dataTransfer.files.length > 0) {
            input.files = event.dataTransfer.files;
            input.dispatchEvent(new Event("change", { bubbles: true }));
        }
    });
}


// ============================================
// REPORT CONTAINER
// ============================================

function getReportContainer() {
    let container = $("deepTruthReport");

    if (container) return container;

    container = document.createElement("div");
    container.id = "deepTruthReport";
    container.className = "panel";
    container.style.marginTop = "20px";

    const page = $("page-investigation");

    if (page) page.appendChild(container);

    return container;
}


// ============================================
// UPLOAD AND ANALYZE
// ============================================

async function uploadMedia() {
    const input = $("mediaFile");
    const button = $("scanButton");

    if (!input || !input.files.length) {
        setStatus("Please select a media file first.", true);
        return;
    }

    const file = input.files[0];

    if (file.size > 100 * 1024 * 1024) {
        setStatus("File size must be below 100 MB.", true);
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    if (button) {
        button.disabled = true;
        button.textContent = "Analyzing Media...";
    }

    setStatus("Running forensic analysis...");

    try {
        const response = await fetch(`${API}/analyze`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Analysis failed.");
        }

        latestReport = data;

        showResult(data);

        setStatus("Investigation completed.");

        await loadHistory();
        await loadStatistics();

        openPage("investigation");

    } catch (error) {
        console.error("Analysis error:", error);

        setStatus(error.message, true);

        getReportContainer().innerHTML = `
            <h2>Analysis Error</h2>
            <p>${safe(error.message)}</p>
        `;

    } finally {
        if (button) {
            button.disabled = false;
            button.innerHTML = `
                <span>Start Forensic Scan</span>
                <i class="fa-solid fa-arrow-right"></i>
            `;
        }
    }
}


// ============================================
// REUSABLE CARDS
// ============================================

function analysisCard(title, status, details, note = "") {
    return `
        <div class="analysis-card" style="margin-top:16px;padding:20px;">
            <h3>${safe(title)}</h3>

            <p><strong>Status:</strong> ${safe(status)}</p>

            ${details || ""}

            ${note ? `
                <p style="margin-top:10px;color:#aab6c8;">
                    ${safe(note)}
                </p>
            ` : ""}
        </div>
    `;
}

function getAnalysisStatus(item = {}) {
    if (item.status === "success") return "Analysis completed";
    if (item.status === "not_configured") return "Model not configured";
    if (item.status === "not_available") return "Not available";
    if (item.status === "error") return "Analysis error";
    if (item.status === "inconclusive") return "Inconclusive";

    return item.status || "Status unavailable";
}

function progressBar(value, color) {
    if (value === null) {
        return `<p style="font-size:12px;color:#aab6c8;">Probability not provided by detector.</p>`;
    }

    return `
        <div style="height:9px;background:rgba(130,150,180,.2);border-radius:20px;overflow:hidden;margin:10px 0;">
            <div style="height:100%;width:${value}%;background:${color};border-radius:20px;"></div>
        </div>
    `;
}


// ============================================
// IMAGE METADATA
// ============================================

function metadataHTML(metadata = {}) {
    const fields = [
        ["File format", metadata.format],
        ["Image width", metadata.width ? `${metadata.width} px` : null],
        ["Image height", metadata.height ? `${metadata.height} px` : null],
        ["Camera", metadata.camera],
        ["Editing software", metadata.software],
        ["Creation date", metadata.creation_date],
        ["Embedded prompt", metadata.embedded_prompt]
    ];

    let rows = fields
        .filter(([label, value]) =>
            value !== null && value !== undefined && value !== ""
        )
        .map(([label, value]) => `
            <div style="display:flex;justify-content:space-between;gap:15px;padding:10px 0;border-bottom:1px solid rgba(150,170,200,.15);">
                <span>${safe(label)}</span>
                <strong>${safe(value)}</strong>
            </div>
        `)
        .join("");

    if (!rows) rows = `<p>No additional embedded metadata was found.</p>`;

    if (metadata.prompt_status === "not_found") {
        rows += `
            <p style="margin-top:12px;">
                No original AI prompt was found in the file metadata.
                An original prompt cannot reliably be recovered from pixels alone.
            </p>
        `;
    }

    return rows;
}


// ============================================
// PROVENANCE
// ============================================

function provenanceHTML(provenance = {}) {
    const present = provenance.provenance_found === true;

    return `
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
            <span style="color:${present ? "#54d69a" : "#e5b45c"};font-size:20px;">
                ${present ? "●" : "○"}
            </span>
            <strong>${present ? "Provenance information found" : "No provenance information found"}</strong>
        </div>

        <p>${safe(provenance.message || "No available provenance information was found.")}</p>

        ${provenance.verification
            ? `<p>Verification: ${safe(provenance.verification)}</p>`
            : ""}
    `;
}


// ============================================
// IMAGE REPORT
// ============================================

function imageReportHTML(image = {}) {
    if (image.status !== "success" || !image.verdict) {
        return `
            <div class="analysis-card">
                <h3>Image Detection</h3>
                <p>${safe(image.message || "Image detection could not return a prediction.")}</p>
            </div>
        `;
    }

    const isAI = image.verdict === "ai-generated";
    const verdict = isAI ? "AI-GENERATED" : "REAL";
    const color = isAI ? "#ff7070" : "#54d69a";

    const confidence = validPercent(image.confidence);
    const aiProbability = validPercent(image.ai_probability);
    const realProbability = validPercent(image.real_probability);

    return `
        <div class="analysis-card" style="margin:18px 0;padding:22px;">
            <span class="section-overline">IMAGE CLASSIFICATION</span>

            <h1 style="color:${color};font-size:30px;margin:12px 0;">
                ${verdict}
            </h1>

            <p><strong>Confidence:</strong> ${formatPercent(confidence)}</p>
            ${progressBar(confidence, color)}

            <p><strong>AI probability:</strong> ${formatPercent(aiProbability)}</p>
            <p><strong>Real probability:</strong> ${formatPercent(realProbability)}</p>
            <p><strong>Detection model:</strong> ${safe(image.model || "Not specified")}</p>
            <p style="margin-top:10px;">${safe(image.analysis_note || "")}</p>
        </div>
    `;
}


// ============================================
// VIDEO REPORT
// ============================================

function videoReportHTML(result = {}) {
    const visual = result.visual_deepfake_analysis || {};
    const audio = result.audio_analysis || {};
    const lipsync = result.lip_sync_analysis || {};
    const integrity = result.video_integrity_analysis || {};

    const face = result.face_deepfake_analysis ||
        visual.face_analysis || {};

    // Actual detector values only. No invented percentages.
    const aiProbability = getFirstPercent(result, [
        "ai_probability",
        "ai_probability_percent"
    ]) ?? getFirstPercent(visual, [
        "ai_probability",
        "ai_probability_percent"
    ]);

    const humanProbability = getFirstPercent(result, [
        "human_probability",
        "real_probability"
    ]) ?? getFirstPercent(visual, [
        "human_probability",
        "real_probability"
    ]);

    const explicitVerdict =
        result.overall_verdict ||
        result.video_verdict ||
        visual.video_verdict ||
        visual.overall_verdict ||
        visual.verdict ||
        "";

    const normalized = String(explicitVerdict).toLowerCase();

    let verdict = "INCONCLUSIVE";
    let color = "#e5b45c";
    let explanation = "The available detectors did not provide enough information for a reliable overall classification.";

    if (
        normalized.includes("ai-generated") ||
        normalized.includes("ai generated") ||
        normalized === "fake"
    ) {
        verdict = "AI-GENERATED";
        color = "#ff7070";
        explanation = "The video detector reported AI-generation or fake-content signals.";
    } else if (
        normalized === "real" ||
        normalized === "human" ||
        normalized.includes("authentic") ||
        normalized.includes("camera-captured")
    ) {
        verdict = "HUMAN / REAL";
        color = "#54d69a";
        explanation = "The video detector classified this video as real.";
    } else if (aiProbability !== null && humanProbability !== null) {
        if (aiProbability >= 70 && aiProbability > humanProbability) {
            verdict = "AI-GENERATED";
            color = "#ff7070";
            explanation = "The detector's AI probability indicates strong AI-generation signals.";
        } else if (humanProbability >= 70 && humanProbability > aiProbability) {
            verdict = "HUMAN / REAL";
            color = "#54d69a";
            explanation = "The detector's human probability indicates strong real-video signals.";
        }
    }

    let html = `
        <div class="analysis-card" style="
            margin-top:20px;
            padding:24px;
            border:1px solid ${color}66;
            border-radius:16px;
            text-align:center;
        ">
            <span class="section-overline">VIDEO AUTHENTICITY RESULT</span>

            <h1 style="color:${color};font-size:32px;margin:15px 0;">
                ${verdict}
            </h1>

            <p>${safe(explanation)}</p>

            <div style="
                display:grid;
                grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
                gap:14px;
                margin-top:22px;
                text-align:left;
            ">
                <div style="padding:15px;background:rgba(255,112,112,.07);border-radius:12px;">
                    <p>AI Probability</p>
                    <h2 style="color:#ff7070;">${formatPercent(aiProbability)}</h2>
                    ${progressBar(aiProbability, "#ff7070")}
                </div>

                <div style="padding:15px;background:rgba(84,214,154,.07);border-radius:12px;">
                    <p>Human Probability</p>
                    <h2 style="color:#54d69a;">${formatPercent(humanProbability)}</h2>
                    ${progressBar(humanProbability, "#54d69a")}
                </div>
            </div>

            <p style="font-size:12px;color:#aab6c8;margin-top:14px;">
                Probabilities are displayed only when returned by the backend.
            </p>
        </div>
    `;

    // VISUAL AND FACE DETECTION

    let visualDetails = "";

    if (visual.verdict) {
        visualDetails += `<p><strong>Visual verdict:</strong> ${safe(visual.verdict)}</p>`;
    }

    if (face.verdict) {
        visualDetails += `<p><strong>Face deepfake verdict:</strong> ${safe(face.verdict)}</p>`;
    }

    if (visual.frames_checked !== undefined) {
        visualDetails += `<p><strong>Frames checked:</strong> ${safe(visual.frames_checked)}</p>`;
    }

    if (visual.frames_scored !== undefined) {
        visualDetails += `<p><strong>Frames scored:</strong> ${safe(visual.frames_scored)}</p>`;
    }

    if (visual.fake_frame_score_percent !== undefined) {
        visualDetails += `<p><strong>Fake-frame score:</strong> ${safe(visual.fake_frame_score_percent)}%</p>`;
    }

    html += analysisCard(
        "Visual & Face Deepfake Detection",
        getAnalysisStatus(visual),
        visualDetails,
        visual.analysis_note || visual.message || face.message || ""
    );

    // SUSPICIOUS FRAMES

    const frames =
        visual.suspicious_frames ||
        visual.flagged_frames ||
        visual.frame_results ||
        [];

    let frameDetails = "";

    if (Array.isArray(frames) && frames.length) {
        frameDetails = `
            <div style="overflow-x:auto;">
                <table style="width:100%;border-collapse:collapse;">
                    <thead>
                        <tr>
                            <th style="text-align:left;padding:10px;">Frame</th>
                            <th style="text-align:left;padding:10px;">Timestamp</th>
                            <th style="text-align:left;padding:10px;">Finding</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${frames.slice(0, 30).map(frame => `
                            <tr>
                                <td style="padding:10px;border-top:1px solid rgba(150,170,200,.15);">
                                    ${safe(frame.frame_number ?? frame.frame ?? "N/A")}
                                </td>
                                <td style="padding:10px;border-top:1px solid rgba(150,170,200,.15);">
                                    ${safe(frame.timestamp ?? frame.time ?? "N/A")}
                                </td>
                                <td style="padding:10px;border-top:1px solid rgba(150,170,200,.15);">
                                    ${safe(frame.verdict ?? frame.label ?? frame.finding ?? "Flagged")}
                                </td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            </div>
        `;
    } else {
        frameDetails = `<p>No individual suspicious-frame timestamps were returned by the detector.</p>`;
    }

    html += analysisCard(
        "Suspicious Frame Analysis",
        "Frame-level findings",
        frameDetails
    );

    // AUDIO

    let audioDetails = "";

    if (audio.verdict) {
        audioDetails += `<p><strong>Audio verdict:</strong> ${safe(audio.verdict)}</p>`;
    }

    if (audio.ai_probability !== undefined) {
        audioDetails += `<p><strong>AI audio probability:</strong> ${safe(audio.ai_probability)}%</p>`;
    }

    if (audio.confidence !== undefined) {
        audioDetails += `<p><strong>Confidence:</strong> ${safe(audio.confidence)}%</p>`;
    }

    html += analysisCard(
        "Audio Authenticity",
        getAnalysisStatus(audio),
        audioDetails,
        audio.message || audio.analysis_note || ""
    );

    // LIP SYNC

    let lipsyncDetails = "";

    if (lipsync.verdict) {
        lipsyncDetails += `<p><strong>Verdict:</strong> ${safe(lipsync.verdict)}</p>`;
    }

    if (lipsync.score !== undefined) {
        lipsyncDetails += `<p><strong>Lip-sync score:</strong> ${safe(lipsync.score)}</p>`;
    }

    if (lipsync.message) {
        lipsyncDetails += `<p>${safe(lipsync.message)}</p>`;
    }

    html += analysisCard(
        "Lip-Sync Analysis",
        getAnalysisStatus(lipsync),
        lipsyncDetails,
        lipsync.analysis_note || ""
    );

    // VIDEO INTEGRITY

    const info = integrity.video_info || {};

    let integrityDetails = "";

    if (integrity.verdict) {
        integrityDetails += `<p><strong>Assessment:</strong> ${safe(integrity.verdict)}</p>`;
    }

    if (info.duration_seconds !== undefined) {
        integrityDetails += `<p><strong>Duration:</strong> ${safe(info.duration_seconds)} seconds</p>`;
    }

    if (info.fps !== undefined) {
        integrityDetails += `<p><strong>Frame rate:</strong> ${safe(info.fps)} FPS</p>`;
    }

    if (info.total_frames !== undefined) {
        integrityDetails += `<p><strong>Total frames:</strong> ${safe(info.total_frames)}</p>`;
    }

    if (info.resolution) {
        integrityDetails += `<p><strong>Resolution:</strong> ${safe(info.resolution)}</p>`;
    }

    if (integrity.frames_sampled !== undefined) {
        integrityDetails += `<p><strong>Frames sampled:</strong> ${safe(integrity.frames_sampled)}</p>`;
    }

    if (integrity.duplicate_or_frozen_frame_count !== undefined) {
        integrityDetails += `<p><strong>Duplicate/frozen frames:</strong> ${safe(integrity.duplicate_or_frozen_frame_count)}</p>`;
    }

    if (integrity.abrupt_transition_count !== undefined) {
        integrityDetails += `<p><strong>Unusual transitions:</strong> ${safe(integrity.abrupt_transition_count)}</p>`;
    }

    const findings = Array.isArray(integrity.findings)
        ? integrity.findings
        : [];

    if (findings.length) {
        integrityDetails += `
            <h4>Forensic Findings</h4>
            <ul>
                ${findings.map(item => `
                    <li>
                        <strong>${safe(item.type || "Finding")}</strong>:
                        ${safe(item.count ?? 0)} detected
                    </li>
                `).join("")}
            </ul>
        `;
    }

    html += analysisCard(
        "Video Integrity Analysis",
        getAnalysisStatus(integrity),
        integrityDetails,
        integrity.analysis_note || integrity.message || ""
    );

    // OVERALL

    html += analysisCard(
        "Investigation Summary",
        verdict,
        `<p>${safe(result.overall_assessment || explanation)}</p>`,
        "Detection results are probabilistic indicators, not definitive proof of authenticity."
    );

    return html;
}


// ============================================
// MAIN REPORT DISPLAY
// ============================================

function showResult(data) {
    const report = getReportContainer();

    const result = data.result || data;
    const mediaType = data.media_type || "image";
    const scanId = data.scan_id || data.id;

    const image = result.image_analysis || {};
    const metadata = result.metadata_analysis || {};
    const provenance = result.provenance_analysis || {};
    const audio = result.audio_analysis || {};

    const isImage = mediaType === "image" || !!image.verdict;

    let html = `
        <div class="panel-heading">
            <div>
                <span class="section-overline">INVESTIGATION REPORT</span>
                <h2>Forensic Intelligence Report</h2>
                <p>${safe(data.original_filename || data.filename || "Media investigation")}</p>
            </div>
        </div>
    `;

    // MEDIA PREVIEW

    if (isImage || mediaType === "video") {
        const mediaURL = selectedPreviewURL ||
            (scanId ? `${API}/media/${encodeURIComponent(scanId)}` : null);

        if (mediaURL) {
            if (isImage) {
                html += `
                    <div style="margin:20px 0;">
                        <h3>Uploaded Image</h3>
                        <img src="${safe(mediaURL)}"
                             alt="Investigated image"
                             style="width:100%;max-height:400px;object-fit:contain;border-radius:12px;margin-top:10px;">
                    </div>
                `;
            } else {
                html += `
                    <div style="margin:20px 0;">
                        <h3>Uploaded Video</h3>
                        <video src="${safe(mediaURL)}"
                               controls
                               preload="metadata"
                               style="width:100%;max-height:400px;border-radius:12px;margin-top:10px;">
                        </video>
                    </div>
                `;
            }
        }
    }

    // IMAGE

    if (isImage) {
        html += imageReportHTML(image);

        html += `
            <div class="analysis-card" style="margin-top:16px;">
                <h3>Image Metadata</h3>
                ${metadataHTML(metadata)}
            </div>
        `;
    }

    // VIDEO

    if (mediaType === "video") {
        html += videoReportHTML(result);
    }

    // AUDIO

    if (mediaType === "audio") {
        html += analysisCard(
            "Audio Analysis",
            getAnalysisStatus(audio),
            audio.verdict
                ? `<p><strong>Verdict:</strong> ${safe(audio.verdict)}</p>`
                : "",
            audio.message || audio.analysis_note || ""
        );
    }

    // PROVENANCE

    html += `
        <div class="analysis-card" style="margin-top:16px;">
            <h3>Content Provenance</h3>
            ${provenanceHTML(provenance)}
        </div>
    `;

    // LIMITATIONS

    html += `
        <div class="analysis-card" style="margin-top:16px;">
            <h3>Important Information</h3>
            <p>AI detection results are probabilistic estimates, not definitive proof of authenticity.</p>
            <p>Metadata and provenance may be missing, removed or modified.</p>
        </div>
    `;

    // DELETE

    if (scanId) {
        html += `
            <div style="margin-top:20px;">
                <button class="secondary-button"
                        id="deleteCurrentScan"
                        type="button"
                        style="color:#ff7070;">
                    <i class="fa-solid fa-trash"></i>
                    Delete This Investigation
                </button>
            </div>
        `;
    }

    report.innerHTML = html;

    const deleteButton = $("deleteCurrentScan");

    if (deleteButton && scanId) {
        deleteButton.addEventListener("click", () => {
            deleteInvestigation(scanId);
        });
    }

    report.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


// ============================================
// HISTORY
// ============================================

async function loadHistory() {
    try {
        const response = await fetch(`${API}/history?limit=100`);

        if (!response.ok) {
            throw new Error("Could not load scan history.");
        }

        const scans = await response.json();
        renderHistory(scans);

    } catch (error) {
        console.error("History error:", error);
    }
}

function getHistoryVerdict(scan) {
    const result = scan.result || {};
    const image = result.image_analysis || {};
    const video = result.visual_deepfake_analysis || {};

    return image.verdict ||
        result.overall_verdict ||
        result.video_verdict ||
        video.verdict ||
        result.audio_analysis?.verdict ||
        result.verdict ||
        (scan.media_type === "video"
            ? "Video analysis"
            : scan.media_type === "audio"
                ? "Audio analysis"
                : "Analysis saved");
}

function renderHistory(scans) {
    const recent = $("recentActivity");
    const history = $("historyList");
    const reports = $("reportsList");

    if (!Array.isArray(scans)) return;

    if (scans.length === 0) {
        const empty = `
            <div class="empty-state">
                <h3>No investigations yet</h3>
                <p>Your completed scans will appear here.</p>
            </div>
        `;

        if (recent) recent.innerHTML = empty;
        if (history) history.innerHTML = empty;
        if (reports) reports.innerHTML = empty;

        return;
    }

    const html = scans.map(scan => {
        const id = scan.id ?? scan.scan_id;
        const verdict = getHistoryVerdict(scan);

        const date = scan.created_at
            ? new Date(scan.created_at).toLocaleString()
            : "Date unavailable";

        return `
            <div class="history-item" style="padding:16px;margin:12px 0;border:1px solid rgba(140,160,190,.2);border-radius:12px;">
                <h3>${safe(scan.filename || "Unknown file")}</h3>
                <p><strong>Type:</strong> ${safe(scan.media_type)}</p>
                <p><strong>Finding:</strong> ${safe(verdict)}</p>
                <p><strong>Date:</strong> ${safe(date)}</p>

                <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px;">
                    <button class="secondary-button" type="button" data-view-scan="${safe(id)}">
                        View Report
                    </button>

                    <button class="secondary-button" type="button" data-delete-scan="${safe(id)}" style="color:#ff7070;">
                        <i class="fa-solid fa-trash"></i>
                        Delete
                    </button>
                </div>
            </div>
        `;
    }).join("");

    if (recent) recent.innerHTML = html;
    if (history) history.innerHTML = html;
    if (reports) reports.innerHTML = html;

    document.querySelectorAll("[data-view-scan]").forEach(button => {
        button.addEventListener("click", () => {
            viewScan(button.dataset.viewScan);
        });
    });

    document.querySelectorAll("[data-delete-scan]").forEach(button => {
        button.addEventListener("click", () => {
            deleteInvestigation(button.dataset.deleteScan);
        });
    });
}


// ============================================
// VIEW SAVED INVESTIGATION
// ============================================

async function viewScan(scanId) {
    try {
        clearSelectedPreview();

        const response = await fetch(
            `${API}/history/${encodeURIComponent(scanId)}`
        );

        if (!response.ok) {
            throw new Error("Investigation not found.");
        }

        const data = await response.json();

        latestReport = data;

        showResult(data);
        openPage("investigation");

        setStatus(`Showing investigation #${scanId}`);

    } catch (error) {
        console.error("View report error:", error);
        setStatus(error.message, true);
    }
}


// ============================================
// DELETE INVESTIGATION
// ============================================

async function deleteInvestigation(scanId) {
    const confirmed = window.confirm(
        "Delete this investigation and its uploaded media permanently?"
    );

    if (!confirmed) return;

    try {
        const response = await fetch(
            `${API}/history/${encodeURIComponent(scanId)}`,
            { method: "DELETE" }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Could not delete investigation.");
        }

        if (
            latestReport &&
            String(latestReport.scan_id || latestReport.id) === String(scanId)
        ) {
            latestReport = null;

            const report = $("deepTruthReport");

            if (report) {
                report.innerHTML = `
                    <h2>Investigation deleted</h2>
                    <p>This report has been removed.</p>
                `;
            }
        }

        setStatus("Investigation deleted successfully.");

        await loadHistory();
        await loadStatistics();

    } catch (error) {
        console.error("Delete error:", error);
        setStatus(error.message, true);
    }
}


// ============================================
// DASHBOARD STATISTICS
// ============================================

async function loadStatistics() {
    try {
        const response = await fetch(`${API}/statistics`);

        if (!response.ok) return;

        const stats = await response.json();

        if ($("totalScans")) {
            $("totalScans").textContent = stats.total_scans ?? 0;
        }

        const historyResponse = await fetch(`${API}/history?limit=200`);

        if (historyResponse.ok) {
            const scans = await historyResponse.json();

            let aiCount = 0;
            let realCount = 0;

            scans.forEach(scan => {
                const result = scan.result || {};
                const image = result.image_analysis || {};

                const verdict = String(
                    image.verdict ||
                    result.overall_verdict ||
                    result.video_verdict ||
                    result.visual_deepfake_analysis?.verdict ||
                    ""
                ).toLowerCase();

                if (
                    verdict.includes("ai-generated") ||
                    verdict.includes("ai generated")
                ) aiCount++;

                if (
                    verdict === "real" ||
                    verdict === "human"
                ) realCount++;
            });

            if ($("aiScans")) $("aiScans").textContent = aiCount;
            if ($("humanScans")) $("humanScans").textContent = realCount;

            if ($("totalReports")) {
                $("totalReports").textContent = stats.total_scans ?? 0;
            }
        }

    } catch (error) {
        console.error("Statistics error:", error);
    }
}


// ============================================
// DATABASE BACKUP
// ============================================

async function createBackup() {
    try {
        setStatus("Creating database backup...");

        const response = await fetch(`${API}/backup`, {
            method: "POST"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Backup failed.");
        }

        setStatus("Backup created successfully.");

        return data;

    } catch (error) {
        console.error("Backup error:", error);
        setStatus(error.message, true);
    }
}


// ============================================
// INDEPENDENT PROMPT INVESTIGATION
// ============================================

function setupPromptInvestigation() {
    const input = $("promptImageFile");

    if (!input) return;

    input.addEventListener("change", () => {
        const file = input.files[0];

        const name = $("promptFileName");
        const preview = $("promptImagePreview");
        const result = $("promptResult");

        if (promptPreviewURL) {
            URL.revokeObjectURL(promptPreviewURL);
            promptPreviewURL = null;
        }

        if (name) {
            name.textContent = file ? file.name : "No file selected";
        }

        if (result) result.innerHTML = "";

        if (!file) {
            if (preview) preview.innerHTML = "";
            return;
        }

        if (!file.type.startsWith("image/")) {
            setPromptStatus("Please select an image.", true);
            input.value = "";
            return;
        }

        promptPreviewURL = URL.createObjectURL(file);

        if (preview) {
            preview.innerHTML = `
                <img src="${safe(promptPreviewURL)}"
                     alt="Prompt investigation image"
                     style="width:100%;max-height:350px;object-fit:contain;border-radius:12px;">
            `;
        }
    });

    const button = $("generatePromptButton");

    if (button) {
        button.addEventListener("click", generatePromptFromUpload);
    }
}

async function generatePromptFromUpload() {
    const input = $("promptImageFile");
    const button = $("generatePromptButton");
    const resultBox = $("promptResult");

    if (!input || !input.files.length) {
        setPromptStatus("Please select an image first.", true);
        return;
    }

    const file = input.files[0];

    if (!file.type.startsWith("image/")) {
        setPromptStatus("Only image files are supported.", true);
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    if (button) button.disabled = true;

    setPromptStatus("Generating an estimated image prompt...");

    try {
        const response = await fetch(`${API}/generate-prompt`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Prompt generation failed.");
        }

        const prompt = data.prompt ||
            data.generated_prompt ||
            data.caption ||
            "";

        if (!prompt) {
            throw new Error("No prompt was returned by the model.");
        }

        if (resultBox) {
            resultBox.innerHTML = `
                <div class="analysis-card" style="margin-top:16px;">
                    <h3>Estimated Image Prompt</h3>

                    <p id="generatedPromptText">${safe(prompt)}</p>

                    <button class="secondary-button"
                            type="button"
                            id="copyGeneratedPrompt">
                        Copy Prompt
                    </button>

                    <p style="margin-top:10px;color:#aab6c8;">
                        This is an estimated description, not necessarily the original prompt.
                    </p>
                </div>
            `;

            const copyButton = $("copyGeneratedPrompt");

            if (copyButton) {
                copyButton.addEventListener("click", async () => {
                    try {
                        await navigator.clipboard.writeText(prompt);
                        setPromptStatus("Prompt copied.");
                    } catch {
                        setPromptStatus("Could not copy prompt.", true);
                    }
                });
            }
        }

        setPromptStatus("Estimated prompt generated.");

    } catch (error) {
        console.error("Prompt generation error:", error);
        setPromptStatus(error.message, true);

    } finally {
        if (button) button.disabled = false;
    }
}


// ============================================
// GLOBAL FUNCTIONS
// ============================================

window.uploadMedia = uploadMedia;
window.openPage = openPage;
window.showResult = showResult;
window.viewScan = viewScan;
window.deleteInvestigation = deleteInvestigation;
window.loadHistory = loadHistory;
window.loadStatistics = loadStatistics;
window.createBackup = createBackup;
window.generatePromptFromUpload = generatePromptFromUpload;