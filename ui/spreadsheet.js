async function myFetch(loc, body) {
  const endpoint = String(loc).replace(/^\//, "");
  try {
    if (useInBrowserPython) {
      return pyCall(endpoint, body || {});
    }
    const response = await fetch(endpoint, {
      method: "POST",
      cache: "no-cache",
      redirect: "follow",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    if (response.ok) {
      return await response.json();
    } else {
      alert(
        "encountered an error when running your code; there may be an error message in the terminal where the server was running.",
      );
      return null;
    }
  } catch (e) {
    alert(
      "could not contact the server; is it running?  this could also be caused by an infinite loop in your code, in which case you will need to restart the server and reload this page.",
    );
    return null;
  }
}

let pyodide = null;
let useInBrowserPython = false;

function setStatus(message) {
  const elt = document.getElementById("loadstatus");
  if (!elt) {
    return;
  }
  elt.textContent = message || "";
  elt.style.display = message ? "block" : "none";
}

function pyCall(endpoint, body) {
  const raw = pyodide.runPython(
    `json.dumps(sheet_api.dispatch(${JSON.stringify(endpoint)}, json.loads(${JSON.stringify(
      JSON.stringify(body || {}),
    )})))`,
  );
  return JSON.parse(raw);
}

async function fetchText(name) {
  const response = await fetch(name);
  if (!response.ok) {
    throw new Error("Could not load " + name);
  }
  return await response.text();
}

async function startInBrowserPython() {
  setStatus("Loading Python in the browser (first visit can take a few seconds)…");
  pyodide = await loadPyodide();
  let labSource;
  try {
    labSource = await fetchText("lab.py");
  } catch (e) {
    labSource = await fetchText("llllab.py");
  }
  pyodide.FS.writeFile("lab.py", labSource);
  pyodide.FS.writeFile("sheet_api.py", await fetchText("sheet_api.py"));
  pyodide.runPython("import json, sheet_api");
  useInBrowserPython = true;
  setStatus("");
}

async function probeServer() {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 1200);
  try {
    const response = await fetch("new", {
      method: "POST",
      cache: "no-cache",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!response.ok) {
      return null;
    }
    const data = await response.json();
    if (data && typeof data === "object" && ("ok" in data || "hasTopo" in data)) {
      return data;
    }
    return null;
  } catch (e) {
    clearTimeout(timer);
    return null;
  }
}

// download sheet

async function downloadsheet() {
  const result = await myFetch("generate_json", {});
  const blob = new Blob([result.result], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.getElementById("downloadlink");
  link.href = url;
  link.click();
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);

    reader.readAsText(file);
  });
}

async function loadfromfile() {
  var file = document.getElementById("fileupload").files[0];
  if (typeof file === "undefined") {
    alert("no file selected!");
    return;
  }
  var sheet;
  try {
    const fileData = await readFileAsText(file);
    sheet = JSON.parse(fileData);
    console.assert(sheet[0] == "FRUGALSHEET");
  } catch (e) {
    throw e;
    alert("couldn't load the given file!");
  }
  const cells = sheet[1];
  const result = await myFetch("new");
  for (var i of document
    .getElementById("spreadsheet")
    .querySelectorAll("input")) {
    i.value = "";
  }
  for (const cell of cells) {
    var elt = document.getElementById(`formula_${cell[0]}`);
    elt.value = cell[1];
    elt.onchange();
  }
}

// set up initial spreadsheet

var letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
var spreadsheet = document.getElementById("spreadsheet");
for (var i = -1; i < 30; i++) {
  var therow = document.createElement("tr");
  for (var j = -1; j < letters.length; j++) {
    if (i == -1) {
      var thecell = document.createElement("th");
      thecell.innerText = j == -1 ? "" : "" + letters[j];
    } else if (j == -1) {
      var thecell = document.createElement("th");
      thecell.innerText = "" + i;
    } else {
      cellname = letters[j] + i;
      var thecell = document.createElement("td");
      var valuefield = document.createElement("input");
      valuefield.type = "text";
      valuefield.size = 10;
      valuefield.disabled = true;
      valuefield.value = "";
      valuefield.style.backgroundColor = "#eeeeee";
      valuefield.id = "value_" + cellname;
      thecell.append(valuefield);
      thecell.append(document.createElement("br"));
      var formulafield = document.createElement("input");
      formulafield.type = "text";
      formulafield.size = 10;
      formulafield.id = "formula_" + cellname;
      formulafield.onchange = (function (name) {
        return () => {
          var elt = document.getElementById("formula_" + name);
          if (elt.value === "") {
            var endpoint = "delete_cell";
          } else {
            var endpoint = "set_cell";
          }
          myFetch(endpoint, { location: name, formula: elt.value }).then(
            (response) => {
              if (response.ok) {
                if (elt.value === "") {
                  document.getElementById("value_" + name).value = "";
                }
                console.log(response);
                elt.style.backgroundColor = "";
                console.log(response.values);
                for (var field in response.values) {
                  const valueElt = document.getElementById("value_" + field);
                  valueElt.value = response.values[field];
                  flashCell(valueElt);
                }
              } else {
                elt.style.backgroundColor = "#ff0000";
              }
            },
          );
        };
      })(cellname);
      thecell.append(formulafield);
    }
    therow.append(thecell);
  }
  spreadsheet.append(therow);
}

function flashCell(elt) {
  const normalBorderColor = getComputedStyle(elt).borderColor;
  elt.animate(
    [
      {
        borderColor: normalBorderColor,
        boxShadow: "none",
      },
      {
        borderColor: "#ffd400",
        boxShadow: "0 0 8px 3px rgba(255, 255, 0, 0.9)",
        offset: 0.2,
      },
      {
        borderColor: normalBorderColor,
        boxShadow: "none",
      },
    ],
    {
      duration: 1000,
      easing: "ease-out",
    },
  );
}

async function boot() {
  let initial = await probeServer();
  if (!initial) {
    try {
      await startInBrowserPython();
      initial = await myFetch("new", {});
    } catch (e) {
      setStatus("");
      alert(
        "could not start the spreadsheet. run server.py locally, or host this folder on GitHub Pages so lab.py and sheet_api.py are available.",
      );
      console.error(e);
      return;
    }
  }
  if (initial && !initial.hasTopo) {
    document.getElementById("filetable").style.display = "none";
  }
}

boot();
