document.addEventListener("DOMContentLoaded", () => {
    // 1. Campus Roles "Save to Wishlist" and "Apply & Track"
    document.querySelectorAll(".save-job").forEach(button => {
        button.addEventListener("click", async () => {
            const company = button.dataset.company;
            const role = button.dataset.role;
            const salary = button.dataset.salary || "";
            const stage = button.dataset.stage || "Saved";

            try {
                const response = await fetch("/api/applications", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ company, role, salary, status: stage, notes: "" })
                });
                const data = await response.json();
                if (data.ok) {
                    button.textContent = "Added ✓";
                    button.classList.add("saved");
                    button.disabled = true;
                    // Optional toast or quick notification
                    setTimeout(() => {
                        window.location.reload();
                    }, 600);
                } else {
                    alert(data.message || "Please login first.");
                }
            } catch (err) {
                console.error("Error saving job:", err);
            }
        });
    });

    // 2. Explore roles search filter
    const search = document.getElementById("jobSearch");
    if (search) {
        search.addEventListener("input", () => {
            const query = search.value.toLowerCase().trim();
            document.querySelectorAll(".job-card").forEach(card => {
                const searchStr = (card.dataset.search || "").toLowerCase();
                card.style.display = searchStr.includes(query) ? "" : "none";
            });
        });
    }

    // 3. Auto-detect Hash for Jobs Tabs
    if (window.location.pathname.includes("/jobs")) {
        if (window.location.hash === "#explore") {
            switchJobTab("explore");
        }
    }
});

/* =========================================
   KANBAN PIPELINE TAB SWITCHING & ACTIONS
   ========================================= */

function switchJobTab(tabName) {
    const pipelineView = document.getElementById("viewPipeline");
    const exploreView = document.getElementById("viewExplore");
    const pipelineBtn = document.getElementById("tabBtnPipeline");
    const exploreBtn = document.getElementById("tabBtnExplore");
    const searchWrap = document.getElementById("searchWrapExplore");

    if (tabName === "explore") {
        if (pipelineView) pipelineView.style.display = "none";
        if (exploreView) exploreView.style.display = "block";
        if (pipelineBtn) pipelineBtn.classList.remove("active");
        if (exploreBtn) exploreBtn.classList.add("active");
        if (searchWrap) searchWrap.style.display = "flex";
        window.location.hash = "explore";
    } else {
        if (pipelineView) pipelineView.style.display = "block";
        if (exploreView) exploreView.style.display = "none";
        if (pipelineBtn) pipelineBtn.classList.add("active");
        if (exploreBtn) exploreBtn.classList.remove("active");
        if (searchWrap) searchWrap.style.display = "none";
        window.location.hash = "pipeline";
    }
}

// Stage change via dropdown
async function changeAppStage(appId, newStage, selectEl) {
    try {
        const response = await fetch(`/api/applications/${appId}/status`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStage })
        });
        const data = await response.json();
        if (data.ok) {
            // Smoothly reload to update counts and columns
            window.location.reload();
        } else {
            alert(data.message || "Could not update status.");
        }
    } catch (err) {
        console.error("Stage update error:", err);
        alert("Failed to update application stage.");
    }
}

// Delete application from tracking
async function deleteApp(appId, btnEl) {
    if (!confirm("Remove this application from your pipeline?")) return;
    try {
        const response = await fetch(`/api/applications/${appId}`, {
            method: "DELETE"
        });
        const data = await response.json();
        if (data.ok) {
            const card = btnEl.closest(".kanban-card");
            if (card) {
                card.style.transition = "all .25s ease";
                card.style.opacity = "0";
                card.style.transform = "scale(0.9)";
                setTimeout(() => {
                    window.location.reload();
                }, 250);
            }
        } else {
            alert(data.message || "Failed to remove application.");
        }
    } catch (err) {
        console.error("Delete error:", err);
    }
}

// Modal open / close
function openAddJobModal(initialStage = "Applied") {
    const modal = document.getElementById("addJobModal");
    const statusSelect = document.getElementById("modalStatus");
    if (statusSelect && initialStage) {
        statusSelect.value = initialStage;
    }
    if (modal) {
        modal.style.display = "flex";
        const companyInput = document.getElementById("modalCompany");
        if (companyInput) companyInput.focus();
    }
}

function closeAddJobModal() {
    const modal = document.getElementById("addJobModal");
    if (modal) modal.style.display = "none";
}

// Submit custom application
async function submitCustomJob(event) {
    event.preventDefault();
    const company = document.getElementById("modalCompany").value.trim();
    const role = document.getElementById("modalRole").value.trim();
    const salary = document.getElementById("modalSalary").value.trim();
    const status = document.getElementById("modalStatus").value;
    const notes = document.getElementById("modalNotes").value.trim();

    if (!company || !role) {
        alert("Please enter both Company and Role.");
        return;
    }

    try {
        const response = await fetch("/api/applications", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ company, role, salary, status, notes })
        });
        const data = await response.json();
        if (data.ok) {
            closeAddJobModal();
            window.location.reload();
        } else {
            alert(data.message || "Could not create application.");
        }
    } catch (err) {
        console.error("Submit error:", err);
    }
}

/* =========================================
   INTERACTIVE 30-DAY ROADMAP INTERACTIONS
   ========================================= */

async function toggleMilestone(taskId, checkboxEl) {
    const row = checkboxEl.closest(".task-row");
    checkboxEl.disabled = true;

    try {
        const response = await fetch("/api/roadmap/toggle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task_id: taskId })
        });
        const data = await response.json();
        if (data.ok) {
            // Update row appearance
            if (data.is_completed) {
                row.classList.add("is-completed");
                checkboxEl.checked = true;
            } else {
                row.classList.remove("is-completed");
                checkboxEl.checked = false;
            }

            // Update top progress metrics
            const pctDisplay = document.getElementById("roadmapPctDisplay");
            const countDisplay = document.getElementById("roadmapCountDisplay");
            const bar = document.getElementById("roadmapProgressBar");
            const badge = document.getElementById("roadmapStatusBadge");

            if (pctDisplay) pctDisplay.textContent = `${data.percentage}%`;
            if (countDisplay) countDisplay.textContent = `${data.completed_count} of ${data.total_tasks} milestones done`;
            if (bar) bar.style.width = `${data.percentage}%`;

            if (badge) {
                if (data.percentage >= 80) {
                    badge.innerHTML = `<span class="badge-pill green-pill">🚀 Drive Ready</span>`;
                } else if (data.percentage >= 40) {
                    badge.innerHTML = `<span class="badge-pill purple-pill">⚡ Strong Momentum</span>`;
                } else {
                    badge.innerHTML = `<span class="badge-pill blue-pill">🌱 Foundation Phase</span>`;
                }
            }

            // Update filter pill counts
            const pillCompleted = document.getElementById("filterCountCompleted");
            const pillPending = document.getElementById("filterCountPending");
            if (pillCompleted) pillCompleted.textContent = data.completed_count;
            if (pillPending) pillPending.textContent = data.total_tasks - data.completed_count;

            // Recalculate current week card stats
            const weekCard = row.closest(".week-card");
            if (weekCard) {
                const totalInWeek = weekCard.querySelectorAll(".task-row").length;
                const completedInWeek = weekCard.querySelectorAll(".task-row.is-completed").length;
                const weekPct = Math.round((completedInWeek / totalInWeek) * 100);
                const weekId = weekCard.dataset.weekId;

                const fractionEl = document.getElementById(`fraction-${weekId}`);
                const miniBarEl = document.getElementById(`bar-${weekId}`);
                if (fractionEl) fractionEl.textContent = `${completedInWeek}/${totalInWeek} Done`;
                if (miniBarEl) miniBarEl.style.width = `${weekPct}%`;
            }
        }
    } catch (err) {
        console.error("Roadmap toggle error:", err);
    } finally {
        checkboxEl.disabled = false;
    }
}

// Filter Roadmap Tasks
function filterRoadmap(type, pillEl) {
    document.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
    pillEl.classList.add("active");

    const rows = document.querySelectorAll(".task-row");
    rows.forEach(row => {
        const isDone = row.classList.contains("is-completed");
        if (type === "completed") {
            row.style.display = isDone ? "flex" : "none";
        } else if (type === "pending") {
            row.style.display = !isDone ? "flex" : "none";
        } else {
            row.style.display = "flex";
        }
    });
    // Toggle single week accordion
    function toggleWeekCard(headerEl) {
        const card = headerEl.closest(".week-card");
        const list = card.querySelector(".week-tasks-list");
        const chevron = headerEl.querySelector(".week-chevron");
        if (!list) return;

        if (list.style.display === "none") {
            list.style.display = "block";
            if (chevron) chevron.style.transform = "rotate(0deg)";
        } else {
            list.style.display = "none";
            if (chevron) chevron.style.transform = "rotate(-90deg)";
        }
    }

    // Toggle all weeks at once
    let allWeeksCollapsed = false;
    function toggleAllWeeks() {
        allWeeksCollapsed = !allWeeksCollapsed;
        const btn = document.getElementById("toggleAllWeeksBtn");
        const lists = document.querySelectorAll(".week-tasks-list");
        const chevrons = document.querySelectorAll(".week-chevron");

        lists.forEach(l => {
            l.style.display = allWeeksCollapsed ? "none" : "block";
        });
        chevrons.forEach(c => {
            c.style.transform = allWeeksCollapsed ? "rotate(-90deg)" : "rotate(0deg)";
        });
        if (btn) {
            btn.textContent = allWeeksCollapsed ? "Expand All Weeks ▸" : "Collapse All Weeks ▾";
        }
    }

    /* =========================================
       MOCK INTERVIEW & TOOLS (PRESERVED)
       ========================================= */


    function showHint(button) {
        const hint = button.parentElement.querySelector(".hint");
        if (hint) hint.classList.toggle("show");
    }

    function startInterview() {
        const card = document.querySelector(".question-card");
        if (card) card.scrollIntoView({ behavior: "smooth" });
    }

    function scoreInterview() {
        const answers = [...document.querySelectorAll(".question-card textarea")];
        const answered = answers.filter(a => a.value.trim().length > 20).length;
        const score = answers.length ? Math.round((answered / answers.length) * 100) : 0;
        const result = document.getElementById("interviewResult");
        if (result) {
            result.innerHTML = `<div class="interview-score">Session score: <b>${score}%</b> · ${answered}/${answers.length} detailed answers</div>`;
            result.scrollIntoView({ behavior: "smooth" });
        }
    }