const outputBoxEl = document.getElementById("output");
outputBoxEl.contentEditable = "false";

let currentPid = null;
let pollTimer = null;
let emptyPollCount = 0;
let isWaitingForInput = false;
let sessionOutput = "";

function switchTab(tab) {

    document.querySelectorAll(".tab-content").forEach(el => {
        el.classList.remove("active")
    })

    document.querySelectorAll(".tab-btn").forEach(el => {
        el.classList.remove("active")
    })

    document.getElementById(tab).classList.add("active")

    document.querySelectorAll(".tab-btn").forEach(btn => {
        if (btn.innerText.toLowerCase() === tab) {
            btn.classList.add("active")
        }
    })
}

function runCode() {
    const code = editor.getValue();
    const outputBox = outputBoxEl;

    stopSession();

    outputBox.innerText = "Running...";
    outputBox.style.color = "#111827";
    sessionOutput = "";

    document.getElementById('ast').innerText = "";
    document.getElementById('cfg').innerText = "";
    document.getElementById('bytecode').innerText = "";

    fetch("/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: code })
    })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                outputBox.innerText = typeof data.error === "object"
                    ? data.error.type + ":\n" + data.error.message
                    : data.error;
                outputBox.style.color = "red";
                return;
            }

            currentPid = data.pid;
            emptyPollCount = 0;
            isWaitingForInput = false;
            sessionOutput = "";
            outputBox.innerText = "";

            renderASTTree(data.ast_json || null);
            document.getElementById('cfg').innerText = data.cfg || "";
            document.getElementById('bytecode').innerText = data.bytecode || "";

            pollTimer = setInterval(pollOutput, 150);
        })
        .catch(() => {
            outputBox.innerText = "Error communicating with server.";
            outputBox.style.color = "red";
        });
}

function pollOutput() {
    if (!currentPid) return;

    const pid = currentPid;

    fetch(`/output/${pid}`)
        .then(res => res.json())
        .then(data => {
            if (!currentPid) return;

            const outputBox = outputBoxEl;

            if (data.error) {
                stopSession();
                outputBox.innerText = sessionOutput + "\n" + data.error;
                outputBox.style.color = "red";
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

            if (data.finished) {
                stopSession();
                outputBox.style.color = "#111827";
                if (!sessionOutput) {
                    outputBox.innerText = "(no output)";
                }
            }
        })
        .catch(() => stopSession());
}

function showInputRow() {
    isWaitingForInput = true;
    const row = document.getElementById('input-row');
    row.style.display = 'flex';
    document.getElementById('user-input-field').focus();
}

function hideInputRow() {
    const row = document.getElementById('input-row');
    row.style.display = 'none';
    document.getElementById('user-input-field').value = '';
}

function submitInput() {
    if (!currentPid || !isWaitingForInput) return;

    const inputField = document.getElementById('user-input-field');
    const value = inputField.value;

    sessionOutput += value + "\n";
    outputBoxEl.innerText = sessionOutput;

    hideInputRow();
    emptyPollCount = 0;
    isWaitingForInput = false;

    fetch(`/input/${currentPid}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input: value })
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

    const outputBox = outputBoxEl;
    outputBox.innerText = "";
    outputBox.style.color = "#111827";
    outputBox.contentEditable = "false";

    document.getElementById('ast').innerHTML = "";
    document.getElementById('cfg').innerText = "";
    document.getElementById('bytecode').innerText = "";

    editor.setValue("");
}

// ── AST Tree Renderer ────────────────────────────────────────────────

function getASTNodeClass(label) {
    const type = label.split('(')[0];
    const LITERALS = new Set(['Number','Float','String','BoolLiteral','NoneLiteral']);
    const OPS      = new Set(['BinaryOp','UnaryOp','Compare','BoolOp']);
    const CONTROLS = new Set(['IfStatement','WhileLoop','ForLoop','ForInLoop',
                               'Return','Break','Continue','Pass']);
    const FUNCS    = new Set(['FunctionDef','FunctionCall','ClassDef',
                               'ClassInstantiation','MethodCall','MethodCallExpr',
                               'SuperMethodCall']);
    const VARS     = new Set(['Variable','Assignment','AttributeAssignment',
                               'AugmentedAssignment','AttributeAugAssignment',
                               'AttributeAccess','AttributeAccessExpr',
                               'IndexAssignment','ListAccess','ExprSubscript']);
    if (type === 'Program')   return 'ast-root';
    if (LITERALS.has(type))   return 'ast-literal';
    if (OPS.has(type))        return 'ast-op';
    if (CONTROLS.has(type))   return 'ast-control';
    if (FUNCS.has(type))      return 'ast-func';
    if (VARS.has(type))       return 'ast-var';
    return 'ast-other';
}

function buildASTNode(data) {
    const li = document.createElement('li');
    const hasChildren = Array.isArray(data.children) && data.children.length > 0;

    const span = document.createElement('span');
    span.className = `ast-node ${getASTNodeClass(data.label)}${hasChildren ? ' has-children' : ''}`;
    span.appendChild(document.createTextNode(data.label));

    if (hasChildren) {
        const toggle = document.createElement('span');
        toggle.className = 'ast-toggle';
        toggle.textContent = '\u25be';
        span.appendChild(toggle);
        span.addEventListener('click', function () {
            const collapsed = li.classList.toggle('ast-collapsed');
            toggle.textContent = collapsed ? '\u25b8' : '\u25be';
        });
    }

    li.appendChild(span);

    if (hasChildren) {
        const ul = document.createElement('ul');
        data.children.forEach(child => ul.appendChild(buildASTNode(child)));
        li.appendChild(ul);
    }

    return li;
}

function renderASTTree(astData) {
    const container = document.getElementById('ast');
    container.innerHTML = '';
    if (!astData) return;

    const wrapper = document.createElement('div');
    wrapper.className = 'ast-tree';

    const rootUl = document.createElement('ul');
    rootUl.appendChild(buildASTNode(astData));
    wrapper.appendChild(rootUl);

    container.appendChild(wrapper);
}

const menu = document.getElementById("editor-menu");
const editorEl = document.getElementById("editor");

editorEl.addEventListener("contextmenu", function(e){

    e.preventDefault();

    menu.style.display = "block";
    menu.style.left = e.pageX + "px";
    menu.style.top = e.pageY + "px";

});

document.addEventListener("click", function(){
    menu.style.display = "none";
});

function menuCut(){
    document.execCommand("cut");
}

function menuCopy(){
    document.execCommand("copy");
}

function menuPaste(){
    document.execCommand("paste");
}