function runCode() {
    const code = editor.getValue();

    fetch("/run", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ code: code })
    })
    .then(res => res.json())
    .then(data => {
        const outputBox = document.getElementById("output");

        if (data.error) {
            outputBox.innerText = data.error;
        } else {
            outputBox.innerText = data.output;
        }
    });
}