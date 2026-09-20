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
  if (data?.schemaVersion !== 3 || !meta || !Number.isInteger(meta.taskCount) || meta.taskCount < 1 ||
      !Number.isInteger(meta.bonusTaskCount) || meta.bonusTaskCount < 0 ||
      !validNumber(meta.maxScore, Number.MIN_VALUE, Number.MAX_SAFE_INTEGER) ||
      !Array.isArray(data.participants) || !data.participants.length || meta.participantCount !== data.participants.length) {
    throw new Error("Invalid leaderboard data");
  }
  const ids = new Set();
  const scoreRanks = new Map();
  const scoreCounts = new Map();
  for (const [index, participant] of data.participants.entries()) {
    if (typeof participant.id !== "string" || !participant.id || ids.has(participant.id) ||
        typeof participant.name !== "string" || !participant.name.trim() || participant.rank !== index + 1 ||
        !validNumber(participant.score, 0, meta.maxScore) || !validNumber(participant.progress, 0, 100) ||
        !Array.isArray(participant.tasks) || participant.tasks.length !== meta.taskCount ||
        participant.tasks.some((task) => typeof task !== "boolean") ||
        participant.completedTasks !== participant.tasks.filter(Boolean).length ||
        !Array.isArray(participant.bonusTasks) || participant.bonusTasks.length !== meta.bonusTaskCount ||
        participant.bonusTasks.some((task) => typeof task !== "boolean") ||
        participant.completedBonusTasks !== participant.bonusTasks.filter(Boolean).length) {
      throw new Error("Invalid participant data");
    }
    ids.add(participant.id);
    if (!scoreRanks.has(participant.score)) scoreRanks.set(participant.score, index + 1);
    scoreCounts.set(participant.score, (scoreCounts.get(participant.score) || 0) + 1);
  }
  for (const participant of data.participants) {
    if (participant.displayRank !== scoreRanks.get(participant.score) || participant.tieCount !== scoreCounts.get(participant.score)) {
      throw new Error("Invalid rank or score tie");
    }
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
    if (participant.displayRank <= 3) button.classList.add(`top-${participant.displayRank}`);
    button.classList.toggle("selected", selectedId === participant.id);
    const bonusDescription = meta.bonusTaskCount ? ` ${participant.completedBonusTasks} of ${meta.bonusTaskCount} optional bonus activities completed.` : "";
    const tieDescription = participant.tieCount > 1 ? `, tied on score with ${participant.tieCount - 1} other ${participant.tieCount === 2 ? "participant" : "participants"}` : "";
    button.setAttribute("aria-label", `${participant.name}, rank ${participant.displayRank}${tieDescription}, score ${format(participant.score)} out of ${format(meta.maxScore)}, ${participant.completedTasks} of ${meta.taskCount} required tasks completed, ${percent(participant.progress)} score progress.${bonusDescription} Open participant focus.`);
    $(".rank-badge", row).textContent = String(participant.displayRank).padStart(2, "0");
    $(".rank-tie", row).hidden = participant.tieCount === 1;
    $(".rank-cell", row).title = participant.tieCount > 1 ? `${participant.tieCount} participants share this score. Row order follows the usual tie-breakers.` : `Rank ${participant.displayRank}`;
    $(".participant-name", row).textContent = participant.name;
    $(".bonus-badge", row).hidden = participant.completedBonusTasks === 0;
    $(".bonus-badge-label", row).textContent = meta.bonusTaskCount === 1 ? "Bonus completed" : `${participant.completedBonusTasks} bonus completed`;
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
  $("#focus-rank").textContent = `#${participant.displayRank}`;
  $("#focus-rank-label").textContent = participant.tieCount > 1 ? `Tied on score · ${participant.tieCount} participants` : "Overall rank";
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
  $("#focus-bonus-section").hidden = meta.bonusTaskCount === 0;
  const bonusMilestones = participant.bonusTasks.map((done, bonusIndex) => {
    const milestone = document.createElement("li");
    milestone.className = "bonus-milestone";
    milestone.classList.toggle("completed", done);
    const star = document.createElement("span");
    star.className = "bonus-star";
    star.setAttribute("aria-hidden", "true");
    star.textContent = done ? "★" : "☆";
    const details = document.createElement("span");
    const label = document.createElement("span");
    label.className = "bonus-title";
    label.textContent = meta.bonusTaskCount === 1 ? "Bonus activity" : `Bonus activity ${bonusIndex + 1}`;
    const status = document.createElement("span");
    status.className = "bonus-status";
    status.textContent = done ? "Completed" : "Not completed";
    details.append(label, status);
    milestone.append(star, details);
    return milestone;
  });
  $("#focus-bonus-milestones").replaceChildren(...bonusMilestones);
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
    $("#task-count").textContent = format(leaderboard.metadata.taskCount);
    $("#bonus-summary").hidden = leaderboard.metadata.bonusTaskCount === 0;
    $("#bonus-summary").textContent = `+ ${leaderboard.metadata.bonusTaskCount} bonus`;
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
