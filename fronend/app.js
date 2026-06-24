let user = null;
let picked = null;
let csrfToken = null;

// ── Toast ──────────────────────────────────────────────────────────────────
function toast(msg, type = "") {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.className = `toast show ${type}`;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), 3000);
}

// ── CSRF Token ──────────────────────────────────────────────────────────────────
async function fetchCsrf() {
  try {
    const res = await fetch("/api/csrf-token");
    const data = await res.json();
    csrfToken = data.csrf_token;
  } catch (_) {}
}

// ── API ────────────────────────────────────────────────────────────────────
async function api(method, path, body) {
  const headers = { "Content-Type": "application/json" };

  if (method !== "GET" && csrfToken) {
    headers["X-CSRF-Token"] = csrfToken;
  }

  const res = await fetch("/api" + path, {
    method,
    headers,
    credentials: "same-origin",
    body: body ? JSON.stringify(body) : undefined
  });

  let data = null;
  try {
    data = await res.json();
  } catch (_) {}

  if (!res.ok) throw new Error(data?.error || "Error");
  return data;
}

// ── Utils ──────────────────────────────────────────────────────────────────
function esc(s) {
  return String(s)
    .replace(/&/g,"&amp;")
    .replace(/</g,"&lt;")
    .replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;")
    .replace(/'/g,"&#39;");
}

function plural(n, word) {
  return `${n} ${word}${n !== 1 ? "s" : ""}`;
}

// ── Pages ──────────────────────────────────────────────────────────────────
function goTo(id) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.getElementById(id)?.classList.add("active");

  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));

  const map = { electionsPage: "nbElections", adminPage: "nbAdmin" };
  if (map[id]) document.getElementById(map[id])?.classList.add("active");

  if (id === "electionsPage") loadElections();
  if (id === "adminPage") {
    loadAdminList();
    loadStats();
  }
}

// ── Navbar ─────────────────────────────────────────────────────────────────
function buildNav() {
  const nav = document.getElementById("navRight");
  if (!nav) return;

  if (!user) {
    nav.innerHTML = "";
    return;
  }

  nav.innerHTML = `
    <span class="nav-user">👤 ${esc(user.username)}</span>
    <button class="nav-btn" id="nbElections" onclick="goTo('electionsPage')">Elections</button>
    ${user.is_admin ? `<button class="nav-btn" id="nbAdmin" onclick="goTo('adminPage')">Admin</button>` : ""}
    <button class="nav-btn" onclick="logout()">Logout</button>`;
}

// ── Auth ───────────────────────────────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll(".tab").forEach((t, i) =>
    t.classList.toggle("active", i === (tab === "login" ? 0 : 1)));

  document.getElementById("loginPanel")?.classList.toggle("hidden", tab !== "login");
  document.getElementById("registerPanel")?.classList.toggle("hidden", tab !== "register");
}

async function register() {
  const username = document.getElementById("regUser")?.value.trim();
  const password = document.getElementById("regPass")?.value;

  if (!username || !password) {
    toast("Fill in all fields", "err");
    return;
  }

  try {
    await api("POST", "/register", { username, password });
    toast("Account created! Please log in.", "ok");
    switchTab("login");
    document.getElementById("loginUser").value = username;
  } catch (e) {
    toast(e.message, "err");
  }
}

async function login() {
  const username = document.getElementById("loginUser")?.value.trim();
  const password = document.getElementById("loginPass")?.value;

  if (!username || !password) {
    toast("Fill in all fields", "err");
    return;
  }

  try {
    const data = await api("POST", "/login", { username, password });
    user = data.user;
    buildNav();
    goTo("electionsPage");
    toast(`Welcome, ${user.username}!`, "ok");
  } catch (e) {
    toast(e.message, "err");
  }
}

async function logout() {
  try {
    await api("POST", "/logout");
  } catch (_) {}
  user = null;
  buildNav();
  goTo("authPage");
}

// ── Elections ──────────────────────────────────────────────────────────────
async function loadElections() {
  const el = document.getElementById("electionsList");
  if (!el) return;

  try {
    const data = await api("GET", "/elections");
    const list = data.elections;

    if (!list.length) {
      el.innerHTML = `<div class="empty">No elections yet.</div>`;
      return;
    }

    el.innerHTML = list.map(e => `
      <div class="card">
        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
          <strong>${esc(e.title)}</strong>
          <span class="badge ${e.is_open ? "open" : "closed"}">${e.is_open ? "Open" : "Closed"}</span>
          ${e.has_voted ? `<span class="badge voted">Voted</span>` : ""}
        </div>
        ${e.description ? `<div class="card-desc">${esc(e.description)}</div>` : ""}
        <div class="card-meta">${e.candidate_count} candidates · ${plural(e.total_votes,"vote")}</div>
        <div class="card-actions">
          ${e.is_open && !e.has_voted
            ? `<button class="btn primary" onclick="openVote(${e.id})">Vote</button>`
            : `<button class="btn outline" onclick="openVote(${e.id})">${e.has_voted ? "My Vote" : "View"}</button>`}
          <button class="btn outline" onclick="openResults(${e.id})">Results</button>
        </div>
      </div>`).join("");

  } catch (e) {
    toast(e.message, "err");
  }
}

// ── Vote Page ──────────────────────────────────────────────────────────────
async function openVote(eid) {
  picked = null;

  try {
    const e = await api("GET", `/elections/${eid}`);

    document.getElementById("voteContent").innerHTML = `
      <div class="vote-title">${esc(e.title)}</div>
      ${e.description ? `<div class="vote-desc">${esc(e.description)}</div>` : ""}
      ${e.has_voted ? `<div class="voted-msg">✅ You've already voted in this election.</div>` : ""}
      <div class="cand-list">
        ${(e.candidates || []).map(c => {
          const mine = e.has_voted && c.id === e.voted_candidate_id;
          return `<div class="cand-row ${mine ? "mine" : ""}"
            onclick="${e.is_open && !e.has_voted ? `pick(${c.id}, this)` : "return false;"}">
            <div class="radio"></div>
            <div class="cand-name">${esc(c.name)} ${mine ? "✓" : ""}</div>
          </div>`;
        }).join("")}
      </div>
      ${e.is_open && !e.has_voted
        ? `<button class="btn primary" onclick="submitVote(${eid})">Cast Vote</button>`
        : `<button class="btn outline" onclick="openResults(${eid})">View Results →</button>`}`;

    goTo("votePage");

  } catch (err) {
    toast(err.message, "err");
  }
}

function pick(id, el) {
  document.querySelectorAll(".cand-row").forEach(r => r.classList.remove("picked"));
  el.classList.add("picked");
  picked = id;
}

async function submitVote(eid) {
  if (!picked) {
    toast("Select a candidate first", "err");
    return;
  }

  try {
    await api("POST", "/vote", { election_id: eid, candidate_id: picked });
    toast("Vote cast! ✅", "ok");
    openResults(eid);
  } catch (e) {
    toast(e.message, "err");
  }
}

// ── Results ────────────────────────────────────────────────────────────────
async function openResults(eid) {
  try {
    const data = await api("GET", `/elections/${eid}/results`);

    document.getElementById("resultsContent").innerHTML = `
      <div class="res-title">${esc(data.title)}</div>
      <div class="res-total">${plural(data.total,"vote")} total</div>
      ${data.results.map((r, i) => `
        <div class="res-row">
          <div class="res-top">
            <div class="res-name">${i === 0 && data.total > 0 ? "🏆 " : ""}${esc(r.name)}</div>
            <div class="res-count">${r.votes} · ${r.percent}%</div>
          </div>
          <div class="bar">
            <div class="bar-fill ${i === 0 ? "first" : ""}" style="width:${r.percent}%"></div>
          </div>
        </div>`).join("")}
      ${data.total === 0 ? `<div class="empty">No votes yet.</div>` : ""}`;

    goTo("resultsPage");

  } catch (e) {
    toast(e.message, "err");
  }
}

// ── Admin ──────────────────────────────────────────────────────────────────
function adminTab(tab) {
  document.querySelectorAll(".admin-tabs .tab").forEach(t => t.classList.remove("active"));
  document.getElementById(`atab-${tab}`)?.classList.add("active");

  ["create", "manage", "users", "audit"].forEach(p => {
    document.getElementById(`apanel-${p}`)?.classList.add("hidden");
  });
  document.getElementById(`apanel-${tab}`)?.classList.remove("hidden");

  if (tab === "manage") loadAdminList();
  if (tab === "users")  loadUsers();
  if (tab === "audit")  loadAudit();
}

function addCand() {
  const el = document.getElementById("candFields");
  const count = el.querySelectorAll("input").length + 1;
  const input = document.createElement("input");
  input.className = "input cand";
  input.type = "text";
  input.placeholder = `Candidate ${count}`;
  el.appendChild(input);
}

async function createElection() {
  const title = document.getElementById("elTitle")?.value.trim();
  const description = document.getElementById("elDesc")?.value.trim();
  const candidates = Array.from(document.querySelectorAll(".cand"))
    .map(i => i.value.trim())
    .filter(v => v);

  if (!title || candidates.length < 2) {
    toast("Title and at least 2 candidates required", "err");
    return;
  }

  try {
    await api("POST", "/elections", { title, description, candidates });
    toast("Election created!", "ok");
    document.getElementById("elTitle").value = "";
    document.getElementById("elDesc").value = "";
    document.getElementById("candFields").innerHTML = `
      <input class="input cand" type="text" placeholder="Candidate 1"/>
      <input class="input cand" type="text" placeholder="Candidate 2"/>`;
    adminTab("manage");
  } catch (e) {
    toast(e.message, "err");
  }
}

async function loadAdminList() {
  const el = document.getElementById("adminList");
  if (!el) return;
  try {
    const data = await api("GET", "/elections");
    const list = data.elections;
    el.innerHTML = list.map(e => `
      <div class="admin-row">
        <div>
          <strong>${esc(e.title)}</strong>
          <span class="card-meta"> · ${plural(e.total_votes, "vote")}</span>
        </div>
        <div class="admin-btns">
          <button class="btn outline small" onclick="toggleElec(${e.id})">${e.is_open ? "Close" : "Open"}</button>
          <button class="btn outline small err" onclick="deleteElec(${e.id})">Delete</button>
        </div>
      </div>`).join("");
  } catch (e) { toast(e.message, "err"); }
}

async function toggleElec(eid) {
  try {
    await api("POST", `/elections/${eid}/toggle`);
    loadAdminList();
    loadStats();
  } catch (e) { toast(e.message, "err"); }
}

async function deleteElec(eid) {
  if (!confirm("Delete this election and all its votes?")) return;
  try {
    await api("DELETE", `/elections/${eid}`);
    loadAdminList();
    loadStats();
  } catch (e) { toast(e.message, "err"); }
}

async function loadUsers() {
  const el = document.getElementById("usersList");
  if (!el) return;
  try {
    const list = await api("GET", "/admin/users");
    el.innerHTML = `
      <table class="table">
        <thead><tr><th>User</th><th>Role</th><th>Votes</th><th>Actions</th></tr></thead>
        <tbody>
          ${list.map(u => `
            <tr>
              <td>${esc(u.username)}</td>
              <td>${u.is_admin ? '<span class="badge open">Admin</span>' : "User"}</td>
              <td>${u.total_votes}</td>
              <td>
                ${u.id === user.id ? "" : (u.is_admin 
                  ? `<button class="btn link small" onclick="setAdmin(${u.id}, false)">Revoke</button>`
                  : `<button class="btn link small" onclick="setAdmin(${u.id}, true)">Make Admin</button>`)}
              </td>
            </tr>`).join("")}
        </tbody>
      </table>`;
  } catch (e) { toast(e.message, "err"); }
}

async function setAdmin(uid, make) {
  try {
    await api("POST", `/admin/${make ? "make-admin" : "revoke-admin"}/${uid}`);
    loadUsers();
  } catch (e) {
    toast(e.message, "err");
  }
}

async function loadAudit() {
  const el = document.getElementById("auditList");
  if (!el) return;
  try {
    const list = await api("GET", "/admin/audit");
    el.innerHTML = list.map(a => `
      <div class="audit-item">
        <span class="audit-time">${a.created_at.split(".")[0]}</span>
        <strong>${esc(a.admin_name)}</strong> 
        <span class="audit-act">${esc(a.action.replace("_", " "))}</span>
        ${a.detail ? `<span class="audit-det">${esc(a.detail)}</span>` : ""}
      </div>`).join("");
  } catch (e) { toast(e.message, "err"); }
}

async function loadStats() {
  const el = document.getElementById("statsBar");
  if (!el) return;
  try {
    const s = await api("GET", "/admin/stats");
    el.innerHTML = `
      <div class="stat"><span>Users</span><strong>${s.total_users}</strong></div>
      <div class="stat"><span>Elections</span><strong>${s.total_elections}</strong></div>
      <div class="stat"><span>Votes Cast</span><strong>${s.total_votes}</strong></div>
      <div class="stat"><span>Open Now</span><strong>${s.open_elections}</strong></div>`;
  } catch (e) { toast(e.message, "err"); }
}

// ── Init ───────────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", async () => {
  await fetchCsrf();
  try {
    const data = await api("GET", "/me");
    if (data?.logged_in) {
      user = data.user;
      buildNav();
      goTo("electionsPage");
    }
  } catch (_) {}
});