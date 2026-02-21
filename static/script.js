let currentPID = null;
let isWaitingInput = false;
let lastOutputLength = 0;

const outputBoxEl = document.getElementById("output");
outputBoxEl.contentEditable = "false"; // locked until a run starts

function runCode() {
    const code = editor.getValue();
    const outputBox = outputBoxEl;

    outputBox.innerText = "";
    outputBox.style.color = "#111827";
    lastOutputLength = 0;
    outputBox.contentEditable = "true";

    const stopExisting = currentPID
        ? fetch("/reset", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ pid: currentPID })
          }).finally(() => {
              currentPID = null;
          })
        : Promise.resolve();

    stopExisting.finally(() => {
        fetch("/run", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({code: code})
        })
        .then(res => res.json())
        .then(data => {
            currentPID = data.pid;
            pollOutput();
        });
    });
}

function pollOutput() {
    if (!currentPID) return;

    fetch("/output", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({pid: currentPID})
    })
    .then(res => res.json())
    .then(data => {

        if (data.output) {
            const outputBox = outputBoxEl;
            outputBox.innerText += data.output;
            lastOutputLength += data.output.length;
            outputBox.scrollTop = outputBox.scrollHeight;
        }

        if (data.finished) {
            const outputBox = outputBoxEl;
            outputBox.innerText += (outputBox.innerText.endsWith("\n") ? "" : "\n") + "[Process finished]\n";
            lastOutputLength = outputBox.innerText.length;
            outputBox.contentEditable = "false";
            currentPID = null;
            isWaitingInput = false;
            return;
        }

        setTimeout(pollOutput, 50);
    });
}

document.getElementById("output").addEventListener("keydown", function(e) {
    if (!currentPID) {
        e.preventDefault();
        return;
    }

    if (e.key === "Enter") {
        e.preventDefault();
        const typed = this.innerText.slice(lastOutputLength);
        const inputText = typed.split("\n").pop();

        if (!inputText.trim()) {
            this.innerText += "\n";
            return;
        }

        fetch("/input", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                pid: currentPID,
                input: inputText
            })
        });

        this.innerText += "\n";
        lastOutputLength = this.innerText.length;
    }
});

function resetCompiler() {
    if (currentPID) {
        fetch("/reset", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({pid: currentPID})
        });
    }

    const outputBox = outputBoxEl;
    outputBox.innerText = "";
    outputBox.style.color = "#111827";
    lastOutputLength = 0;
    outputBox.contentEditable = "false";

    editor.setValue("");
    currentPID = null;
}