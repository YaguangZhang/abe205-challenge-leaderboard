const $ = (selector, root = document) => root.querySelector(selector);
const list = $("#participant-list");
const searchInput = $("#search-input");
const dialog = $("#focus-dialog");
const template = $("#participant-template");
const numberFormat = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
const percentFormat = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
let leaderboard;
let selectedId = null;
let returnFocus = null;

const format = (value) => numberFormat.format(value);
const percent = (value) => `${percentFormat.format(value)}%`;
const searchKey = (value) => value.normalize("NFKD").replace(/\p{M}/gu, "").toLocaleLowerCase("en-US");
const validNumber = (value, min, max) => typeof value === "number" && Number.isFinite(value) && value >= min && value <= max;

function validateData(data) {
  const meta = data?.metadata;
  if (data?.schemaVersion !== 1 || !meta || !Number.isInteger(meta.taskCount) || meta.taskCount < 1 ||
      !validNumber(meta.maxScore, Number.MIN_VALUE, Number.MAX_SAFE_INTEGER) ||
      !Array.isArray(data.participants) || !data.participants.length || meta.participantCount !== data.participants.length) {
    throw new Error("Invalid leaderboard data");
  }
  const ids = new Set();
  for (const [index, participant] of data.participants.entries()) {
    if (typeof participant.id !== "string" || !participant.id || ids.has(participant.id) ||
        typeof participant.name !== "string" || !participant.name.trim() || participant.rank !== index + 1 ||
        !validNumber(participant.score, 0, meta.maxScore) || !validNumber(participant.progress, 0, 100) ||
        !Array.isArray(participant.tasks) || participant.tasks.length !== meta.taskCount ||
        participant.tasks.some((task) => typeof task !== "boolean") ||
        participant.completedTasks !== participant.tasks.filter(Boolean).length) {
      throw new Error("Invalid participant data");
    }
    ids.add(participant.id);
  }
  return data;
}

function renderRows() {
  const query = searchKey(searchInput.value.trim());
  const participants = leaderboard.participants.filter((p) => searchKey(p.name).includes(query));
  const fragment = document.createDocumentFragment();
  const meta = leaderboard.metadata;
  for (const [index, participant] of participants.entries()) {
    const row = template.content.firstElementChild.cloneNode(true);
    const button = $("button", row);
    row.style.setProperty("--index", index);
    button.dataset.id = participant.id;
    button.style.setProperty("--progress", `${participant.progress}%`);
    if (participant.rank <= 3) button.classList.add(`top-${participant.rank}`);
    button.classList.toggle("selected", selectedId === participant.id);
    button.setAttribute("aria-label", `${participant.name}, rank ${participant.rank}, score ${format(participant.score)} out of ${format(meta.maxScore)}, ${participant.completedTasks} of ${meta.taskCount} tasks completed, ${percent(participant.progress)} progress. Open participant focus.`);
    $(".rank-badge", row).textContent = String(participant.rank).padStart(2, "0");
    $(".participant-name", row).textContent = participant.name;
    $(".task-number", row).textContent = `${participant.completedTasks} / ${meta.taskCount}`;
    $(".progress-number", row).textContent = percent(participant.progress);
    $(".score-cell strong", row).textContent = format(participant.score);
    $(".score-cell > span", row).textContent = `/ ${format(meta.maxScore)}`;
    fragment.append(row);
  }
  list.replaceChildren(fragment);
  $("#empty-state").hidden = participants.length > 0;
  $("#clear-search").hidden = searchInput.value.length === 0;
  $("#results-count").textContent = query ? `${participants.length} of ${meta.participantCount} participants` : `${meta.participantCount} participants`;
}

function clearSearch() {
  searchInput.value = "";
  renderRows();
  searchInput.focus();
}

function focusParticipant(id) {
  const index = leaderboard.participants.findIndex((p) => p.id === id);
  if (index < 0) return;
  const participant = leaderboard.participants[index];
  const meta = leaderboard.metadata;
  selectedId = id;
  for (const button of list.querySelectorAll(".participant")) {
    const selected = button.dataset.id === id;
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-expanded", String(selected));
  }
  $("#focus-name").textContent = participant.name;
  $("#focus-rank").textContent = `#${participant.rank}`;
  $("#focus-score").textContent = format(participant.score);
  $("#focus-max").textContent = `/ ${format(meta.maxScore)}`;
  $("#focus-percent").textContent = percent(participant.progress);
  const progress = $("#focus-progress");
  progress.style.setProperty("--progress", `${participant.progress}%`);
  progress.setAttribute("aria-valuenow", participant.progress);
  progress.setAttribute("aria-valuetext", percent(participant.progress));
  $("#focus-tasks").textContent = `${participant.completedTasks} / ${meta.taskCount} completed`;
  const milestones = participant.tasks.map((done, taskIndex) => {
    const milestone = document.createElement("li");
    milestone.classList.toggle("completed", done);
    const label = document.createElement("span");
    label.className = "sr-only";
    label.textContent = `Task ${taskIndex + 1}: ${done ? "completed" : "pending"}`;
    const symbol = document.createElement("span");
    symbol.setAttribute("aria-hidden", "true");
    symbol.textContent = done ? "✓" : "·";
    milestone.append(label, symbol);
    return milestone;
  });
  $("#focus-milestones").replaceChildren(...milestones);
  $("#completion-message").hidden = participant.progress !== 100;
  $("#previous-participant").disabled = index === 0;
  $("#next-participant").disabled = index === leaderboard.participants.length - 1;
  $("#focus-position").textContent = `${participant.rank} / ${meta.participantCount}`;
  if (!dialog.open) {
    returnFocus = document.activeElement;
    dialog.showModal();
  }
}

function adjacentParticipant(offset) {
  const index = leaderboard.participants.findIndex((p) => p.id === selectedId);
  const participant = leaderboard.participants[index + offset];
  if (participant) focusParticipant(participant.id);
}

async function loadLeaderboard() {
  $("#loading-state").hidden = false;
  $("#error-state").hidden = true;
  list.setAttribute("aria-busy", "true");
  $("#retry").disabled = true;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(new URL("./data/leaderboard.json", import.meta.url), { cache: "no-store", signal: controller.signal });
    if (!response.ok) throw new Error("Data unavailable");
    leaderboard = validateData(await response.json());
    $("#participant-count").textContent = format(leaderboard.metadata.participantCount);
    $("#task-count").textContent = String(leaderboard.metadata.taskCount).padStart(2, "0");
    $("#max-score").textContent = format(leaderboard.metadata.maxScore);
    searchInput.disabled = false;
    renderRows();
  } catch {
    $("#error-state").hidden = false;
    $("#results-count").textContent = "Standings unavailable";
    searchInput.disabled = true;
    list.replaceChildren();
  } finally {
    clearTimeout(timeout);
    $("#loading-state").hidden = true;
    $("#retry").disabled = false;
    list.setAttribute("aria-busy", "false");
  }
}

$(".search").addEventListener("submit", (event) => event.preventDefault());
searchInput.addEventListener("input", renderRows);
$("#clear-search").addEventListener("click", clearSearch);
$("#reset-search").addEventListener("click", clearSearch);
$("#retry").addEventListener("click", loadLeaderboard);
list.addEventListener("click", (event) => {
  const button = event.target.closest(".participant");
  if (button) focusParticipant(button.dataset.id);
});
$("#close-focus").addEventListener("click", () => dialog.close());
$("#previous-participant").addEventListener("click", () => adjacentParticipant(-1));
$("#next-participant").addEventListener("click", () => adjacentParticipant(1));
dialog.addEventListener("click", (event) => {
  if (event.target !== dialog) return;
  const rect = dialog.getBoundingClientRect();
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
});
dialog.addEventListener("close", () => {
  for (const button of list.querySelectorAll(".participant")) button.setAttribute("aria-expanded", "false");
  // Keep the last person highlighted and return keyboard focus to their row.
  const selected = Array.from(list.querySelectorAll(".participant")).find((button) => button.dataset.id === selectedId);
  (selected || returnFocus || searchInput).focus({ preventScroll: true });
});

loadLeaderboard();
