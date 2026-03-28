const outputBoxEl = document.getElementById("output");
outputBoxEl.contentEditable = "false";

const aiToggleEl = document.getElementById("ai-toggle");
const aiPaneEl = document.getElementById("ai-pane");
const aiChatEl = document.getElementById("ai-chat");
const aiChatEmptyEl = document.getElementById("ai-chat-empty");
const aiPendingBadgeEl = document.getElementById("ai-pending-badge");
const filenameInputEl = document.getElementById("filename-input");

const DEFAULT_FILENAME_BASE = "main";
const FILENAME_STORAGE_KEY = "pyflux-filename";

let aiPrecheckShown = false;
let aiPostcheckShown = false;
let aiHasError = false;

function normalizeFilenameBase(value) {
  const raw = String(value || "").trim();
  if (!raw) return DEFAULT_FILENAME_BASE;

  const sanitized = raw.replace(/[\\/?:%*|"<>]/g, "-");
  const base = sanitized.replace(/\.[^/.]+$/, "").trim();
  return base || DEFAULT_FILENAME_BASE;
}

function getFilenameBase() {
  if (!filenameInputEl) return DEFAULT_FILENAME_BASE;
  const normalized = normalizeFilenameBase(filenameInputEl.value);
  filenameInputEl.value = normalized;
  localStorage.setItem(FILENAME_STORAGE_KEY, normalized);
  return normalized;
}

function getDownloadFilename() {
  return getFilenameBase() + ".py";
}

function downloadCode() {
  if (!window.editor) return;
  const filename = getDownloadFilename();
  const code = editor.getValue();
  const blob = new Blob([code], { type: "text/x-python;charset=utf-8" });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

if (filenameInputEl) {
  const savedName = localStorage.getItem(FILENAME_STORAGE_KEY);
  if (savedName) {
    filenameInputEl.value = normalizeFilenameBase(savedName);
  }

  filenameInputEl.addEventListener("blur", () => {
    getFilenameBase();
  });

  filenameInputEl.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      downloadCode();
    }
  });
}

function setAiPaneOpen(isOpen) {
  if (!aiPaneEl) return;
  aiPaneEl.classList.toggle("is-hidden", !isOpen);
  aiPaneEl.setAttribute("aria-hidden", String(!isOpen));
}

function setAiPendingBadge(isVisible) {
  if (!aiPendingBadgeEl) return;
  aiPendingBadgeEl.classList.toggle("is-hidden", !isVisible);
}

function showAiEmptyState() {
  if (aiChatEmptyEl) aiChatEmptyEl.style.display = "flex";
}

function hideAiEmptyState() {
  if (aiChatEmptyEl) aiChatEmptyEl.style.display = "none";
}

function clearAiChat() {
  if (!aiChatEl) return;
  aiChatEl.innerHTML = "";
  if (aiChatEmptyEl) {
    aiChatEl.appendChild(aiChatEmptyEl);
  }
  showAiEmptyState();
  aiHasError = false;
  setAiPendingBadge(false);
}

function applyAiFix(fixedCode, entryEl) {
  if (!fixedCode || !window.editor) return;
  editor.setValue(fixedCode);
  if (entryEl && entryEl.parentNode) {
    entryEl.parentNode.removeChild(entryEl);
  }

  const hasErrorEntry = Boolean(
    aiChatEl && aiChatEl.querySelector(".ai-chat-entry.ai-error"),
  );
  aiHasError = hasErrorEntry;
  setAiPendingBadge(hasErrorEntry);

  if (aiChatEl && !aiChatEl.querySelector(".ai-chat-entry")) {
    if (aiChatEmptyEl && !aiChatEmptyEl.parentElement) {
      aiChatEl.appendChild(aiChatEmptyEl);
    }
    showAiEmptyState();
  }
}

function showAiMessage(result, sourceLabel) {
  if (!aiChatEl || !result) return;

  const status = String(result.status || "ERROR").toUpperCase();
  const isOk = status === "OK";
  if (isOk && aiHasError) {
    return;
  }
  const message = isOk
    ? "Your code looks good to run."
    : result.message || "AI detected an issue.";

  hideAiEmptyState();

  const entry = document.createElement("div");
  entry.className = "ai-chat-entry " + (isOk ? "ai-ok" : "ai-error");

  const meta = document.createElement("div");
  meta.className = "ai-chat-meta";

  const source = document.createElement("span");
  source.className = "ai-chat-source";
  source.textContent = sourceLabel || "AI Review";

  const statusEl = document.createElement("span");
  statusEl.className = "ai-chat-status";
  statusEl.textContent = status;

  meta.appendChild(source);
  meta.appendChild(statusEl);

  const msg = document.createElement("div");
  msg.className = "ai-chat-message";
  msg.textContent = message;

  entry.appendChild(meta);
  entry.appendChild(msg);

  const fixedCode = result.fixed_code || "";
  if (!isOk && fixedCode) {
    const codeBlock = document.createElement("pre");
    codeBlock.className = "ai-chat-code";
    codeBlock.textContent = fixedCode;
    entry.appendChild(codeBlock);

    const actions = document.createElement("div");
    actions.className = "ai-chat-actions";

    const applyBtn = document.createElement("button");
    applyBtn.type = "button";
    applyBtn.className = "run-btn ai-apply-btn";
    applyBtn.textContent = "Apply Fix";
    applyBtn.addEventListener("click", function () {
      applyAiFix(fixedCode, entry);
    });

    actions.appendChild(applyBtn);
    entry.appendChild(actions);
  }

  aiChatEl.appendChild(entry);
  aiChatEl.scrollTop = aiChatEl.scrollHeight;
  if (!isOk) {
    aiHasError = true;
    setAiPendingBadge(true);
  } else {
    setAiPendingBadge(false);
  }
  if (aiToggleEl && aiToggleEl.checked) {
    setAiPaneOpen(true);
  }
}

if (aiToggleEl) {
  setAiPaneOpen(aiToggleEl.checked);
  setAiPendingBadge(aiHasError);
  aiToggleEl.addEventListener("change", function () {
    setAiPaneOpen(aiToggleEl.checked);
    if (aiToggleEl.checked && aiChatEl) {
      aiChatEl.scrollTop = aiChatEl.scrollHeight;
    }
  });
}

function toggleTheme() {
  const isDark = document.body.getAttribute("data-theme") === "dark";
  if (isDark) {
    document.body.removeAttribute("data-theme");
    if (window.monaco) monaco.editor.setTheme("formal-light");
    localStorage.setItem("pyflux-theme", "light");
  } else {
    document.body.setAttribute("data-theme", "dark");
    if (window.monaco) monaco.editor.setTheme("formal-dark");
    localStorage.setItem("pyflux-theme", "dark");
  }
  refreshOutputColor();
}

function getTextColor() {
  return document.body.getAttribute("data-theme") === "dark"
    ? "#C2D8F0"
    : "#111827";
}

function setOutputStatus(status) {
  if (!outputBoxEl) return;
  outputBoxEl.dataset.status = status;
  if (status === "error") {
    outputBoxEl.style.color = "red";
  } else {
    outputBoxEl.style.color = getTextColor();
  }
}

function refreshOutputColor() {
  if (!outputBoxEl) return;
  if (outputBoxEl.dataset.status !== "error") {
    outputBoxEl.style.color = getTextColor();
  }
}

function isAiModeEnabled() {
  return Boolean(aiToggleEl && aiToggleEl.checked);
}

let currentPid = null;
let pollTimer = null;
let emptyPollCount = 0;
let isWaitingForInput = false;
let sessionOutput = "";

const _buildingTimers = {};

function showBuildingAnimation(sectionId, label) {
  stopBuildingAnimation(sectionId);
  const el = document.getElementById(sectionId);
  el.innerHTML = "";

  const wrapper = document.createElement("div");
  wrapper.className = "building-anim";

  const text = document.createElement("span");
  text.textContent = "Building " + label;

  const dots = document.createElement("span");
  dots.className = "building-dots";
  dots.textContent = "";

  wrapper.appendChild(text);
  wrapper.appendChild(dots);
  el.appendChild(wrapper);

  let count = 0;
  _buildingTimers[sectionId] = setInterval(() => {
    count = (count % 3) + 1;
    dots.textContent = ".".repeat(count);
  }, 380);
}

function stopBuildingAnimation(sectionId) {
  if (_buildingTimers[sectionId]) {
    clearInterval(_buildingTimers[sectionId]);
    delete _buildingTimers[sectionId];
  }
}

function stopAllBuildingAnimations() {
  stopBuildingAnimation("ast");
  stopBuildingAnimation("cfg");
  stopBuildingAnimation("bytecode");
}

function switchTab(tab) {
  document.querySelectorAll(".tab-content").forEach((el) => {
    el.classList.remove("active");
  });

  document.querySelectorAll(".tab-btn").forEach((el) => {
    el.classList.remove("active");
  });

  document.getElementById(tab).classList.add("active");

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    if (btn.innerText.toLowerCase() === tab) {
      btn.classList.add("active");
    }
  });
}

function runCode() {
  const code = editor.getValue();
  const outputBox = outputBoxEl;

  stopSession();
  clearAiChat();
  aiPrecheckShown = false;
  aiPostcheckShown = false;
  aiHasError = false;

  outputBox.innerText = "Running...";
  setOutputStatus("normal");
  sessionOutput = "";

  showBuildingAnimation("ast", "AST");
  showBuildingAnimation("cfg", "CFG");
  showBuildingAnimation("bytecode", "Bytecode");

  fetch("/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code: code, ai_mode: isAiModeEnabled() }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.error) {
        stopAllBuildingAnimations();
        outputBox.innerText =
          typeof data.error === "object"
            ? data.error.type + ":\n" + data.error.message
            : data.error;
        setOutputStatus("error");
        return;
      }

      currentPid = data.pid;
      emptyPollCount = 0;
      isWaitingForInput = false;
      sessionOutput = "";
      outputBox.innerText = "";

      stopAllBuildingAnimations();
      renderASTTree(data.ast_json || null);
      document.getElementById("cfg").innerText = data.cfg || "";
      document.getElementById("bytecode").innerText = data.bytecode || "";

      if (data.ai_precheck && !aiPrecheckShown) {
        showAiMessage(data.ai_precheck, "Pre-run Review");
        aiPrecheckShown = true;
      }

      pollTimer = setInterval(pollOutput, 150);
    })
    .catch(() => {
      stopAllBuildingAnimations();
      outputBox.innerText = "Error communicating with server.";
      setOutputStatus("error");
    });
}

function pollOutput() {
  if (!currentPid) return;

  const pid = currentPid;

  fetch(`/output/${pid}`)
    .then((res) => res.json())
    .then((data) => {
      if (!currentPid) return;

      const outputBox = outputBoxEl;

      if (data.error) {
        stopSession();
        outputBox.innerText = sessionOutput + "\n" + data.error;
        setOutputStatus("error");
        return;
      }

      if (data.output) {
        sessionOutput += data.output;
        outputBox.innerText = sessionOutput;
        outputBox.scrollTop = outputBox.scrollHeight;
        emptyPollCount = 0;
        if (isWaitingForInput) {
          hideInputRow();
          isWaitingForInput = false;
        }
      } else if (!data.finished) {
        emptyPollCount++;
        if (emptyPollCount >= 5 && !isWaitingForInput) {
          showInputRow();
        }
      }

      if (data.ai_postcheck && !aiPostcheckShown) {
        showAiMessage(data.ai_postcheck, "Post-run Review");
        aiPostcheckShown = true;
      }

      if (data.finished) {
        stopSession();
        setOutputStatus("normal");
        if (!sessionOutput) {
          outputBox.innerText = "(no output)";
        }
      }
    })
    .catch(() => stopSession());
}

function showInputRow() {
  isWaitingForInput = true;
  const row = document.getElementById("input-row");
  row.style.display = "flex";
  document.getElementById("user-input-field").focus();
}

function hideInputRow() {
  const row = document.getElementById("input-row");
  row.style.display = "none";
  document.getElementById("user-input-field").value = "";
}

function submitInput() {
  if (!currentPid || !isWaitingForInput) return;

  const inputField = document.getElementById("user-input-field");
  const value = inputField.value;

  sessionOutput += value + "\n";
  outputBoxEl.innerText = sessionOutput;

  hideInputRow();
  emptyPollCount = 0;
  isWaitingForInput = false;

  fetch(`/input/${currentPid}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ input: value }),
  }).catch(() => {});
}

function stopSession() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  if (currentPid) {
    const pid = currentPid;
    currentPid = null;
    fetch(`/stop/${pid}`, { method: "POST" }).catch(() => {});
  }
  hideInputRow();
  isWaitingForInput = false;
}

function resetCompiler() {
  stopSession();
  sessionOutput = "";
  clearAiChat();
  aiPrecheckShown = false;
  aiPostcheckShown = false;
  aiHasError = false;

  const outputBox = outputBoxEl;
  outputBox.innerText = "";
  setOutputStatus("normal");
  outputBox.contentEditable = "false";

  document.getElementById("ast").innerHTML = "";
  document.getElementById("cfg").innerText = "";
  document.getElementById("bytecode").innerText = "";

  stopAllBuildingAnimations();

  editor.setValue("");
}

function getASTNodeClass(label) {
  const type = label.split("(")[0];
  const LITERALS = new Set([
    "Number",
    "Float",
    "String",
    "BoolLiteral",
    "NoneLiteral",
  ]);
  const OPS = new Set(["BinaryOp", "UnaryOp", "Compare", "BoolOp"]);
  const CONTROLS = new Set([
    "IfStatement",
    "WhileLoop",
    "ForLoop",
    "ForInLoop",
    "Return",
    "Break",
    "Continue",
    "Pass",
  ]);
  const FUNCS = new Set([
    "FunctionDef",
    "FunctionCall",
    "ClassDef",
    "ClassInstantiation",
    "MethodCall",
    "MethodCallExpr",
    "SuperMethodCall",
  ]);
  const VARS = new Set([
    "Variable",
    "Assignment",
    "AttributeAssignment",
    "AugmentedAssignment",
    "AttributeAugAssignment",
    "AttributeAccess",
    "AttributeAccessExpr",
    "IndexAssignment",
    "ListAccess",
    "ExprSubscript",
  ]);
  if (type === "Program") return "ast-root";
  if (LITERALS.has(type)) return "ast-literal";
  if (OPS.has(type)) return "ast-op";
  if (CONTROLS.has(type)) return "ast-control";
  if (FUNCS.has(type)) return "ast-func";
  if (VARS.has(type)) return "ast-var";
  return "ast-other";
}

function buildASTNode(data) {
  const li = document.createElement("li");
  const hasChildren = Array.isArray(data.children) && data.children.length > 0;

  const span = document.createElement("span");
  span.className = `ast-node ${getASTNodeClass(data.label)}${hasChildren ? " has-children" : ""}`;
  span.appendChild(document.createTextNode(data.label));

  if (hasChildren) {
    const toggle = document.createElement("span");
    toggle.className = "ast-toggle";
    toggle.textContent = "\u25be";
    span.appendChild(toggle);
    span.addEventListener("click", function () {
      const collapsed = li.classList.toggle("ast-collapsed");
      toggle.textContent = collapsed ? "\u25b8" : "\u25be";
    });
  }

  li.appendChild(span);

  if (hasChildren) {
    const ul = document.createElement("ul");
    data.children.forEach((child) => ul.appendChild(buildASTNode(child)));
    li.appendChild(ul);
  }

  return li;
}

function renderASTTree(astData) {
  const container = document.getElementById("ast");
  container.innerHTML = "";
  if (!astData) return;

  const wrapper = document.createElement("div");
  wrapper.className = "ast-tree";

  const rootUl = document.createElement("ul");
  rootUl.appendChild(buildASTNode(astData));
  wrapper.appendChild(rootUl);

  container.appendChild(wrapper);
}

const menu = document.getElementById("editor-menu");
const editorEl = document.getElementById("editor");

editorEl.addEventListener("contextmenu", function (e) {
  e.preventDefault();

  menu.style.display = "block";
  menu.style.left = e.pageX + "px";
  menu.style.top = e.pageY + "px";
});

document.addEventListener("click", function () {
  menu.style.display = "none";
});

function menuCut() {
  document.execCommand("cut");
}

function menuCopy() {
  document.execCommand("copy");
}

function menuPaste() {
  document.execCommand("paste");
}
