(function () {
  "use strict";

  const qs = (selector, root) => (root || document).querySelector(selector);
  const qsa = (selector, root) => Array.from((root || document).querySelectorAll(selector));

  function csrfToken() {
    const meta = qs('meta[name="csrf-token"]');
    return meta ? meta.content : "";
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function formatBytes(bytes) {
    if (!bytes) return "0 KB";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + " KB";
    return (bytes / 1024 / 1024).toFixed(1) + " MB";
  }

  function withId(urlTemplate, id) {
    if (!urlTemplate) return "";
    return urlTemplate.replace("/0/", "/" + id + "/");
  }

  function submitPost(url, fields) {
    if (!url) return;

    const form = document.createElement("form");
    form.method = "post";
    form.action = url;
    form.hidden = true;

    const payload = Object.assign(
      {
        csrf_token: csrfToken(),
        next: window.location.pathname + window.location.search
      },
      fields || {}
    );

    Object.keys(payload).forEach(function (name) {
      if (payload[name] === undefined || payload[name] === null) return;
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = name;
      input.value = String(payload[name]);
      form.appendChild(input);
    });

    document.body.appendChild(form);
    form.submit();
  }

  /* -------------------------------------------------------
     Small Markdown renderer (headings, lists, code, links)
     ------------------------------------------------------- */
  function renderInline(text) {
    let out = text;

    out = out.replace(/\[\[([^\]]+)\]\]/g, function (_, name) {
      return (
        '<a href="#" class="wiki-link">' +
        '<i class="bi bi-link-45deg"></i>' +
        "<b>[[" +
        name +
        "]]</b>" +
        "<span>· crear</span>" +
        "</a>"
      );
    });

    out = out.replace(/`([^`]+)`/g, "<code>$1</code>");
    out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    out = out.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
    out = out.replace(
      /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener">$1</a>'
    );

    return out;
  }

  function renderMarkdown(source) {
    const codeBlocks = [];
    let text = String(source || "").replace(/\r\n/g, "\n");

    text = text.replace(/```([\w-]*)\n([\s\S]*?)```/g, function (_, lang, code) {
      codeBlocks.push(
        "<pre><code>" + escapeHtml(code.replace(/\n$/, "")) + "</code></pre>"
      );
      return "\u0000CODE" + (codeBlocks.length - 1) + "\u0000";
    });

    const lines = escapeHtml(text).split("\n");
    let html = "";
    let listType = null;
    let inParagraph = false;

    function closeList() {
      if (listType) {
        html += "</" + listType + ">";
        listType = null;
      }
    }

    function closeParagraph() {
      if (inParagraph) {
        html += "</p>";
        inParagraph = false;
      }
    }

    lines.forEach(function (rawLine) {
      const line = rawLine.trim();
      const codeMatch = line.match(/^\u0000CODE(\d+)\u0000$/);

      if (codeMatch) {
        closeList();
        closeParagraph();
        html += codeBlocks[Number(codeMatch[1])] || "";
        return;
      }

      if (!line) {
        closeList();
        closeParagraph();
        return;
      }

      const heading = line.match(/^(#{1,6})\s+(.*)$/);
      if (heading) {
        closeList();
        closeParagraph();
        const level = heading[1].length;
        html +=
          "<h" +
          level +
          ">" +
          renderInline(heading[2]) +
          "</h" +
          level +
          ">";
        return;
      }

      if (/^(-{3,}|\*{3,}|_{3,})$/.test(line)) {
        closeList();
        closeParagraph();
        html += "<hr>";
        return;
      }

      const quote = line.match(/^>\s?(.*)$/);
      if (quote) {
        closeList();
        closeParagraph();
        html += "<blockquote>" + renderInline(quote[1]) + "</blockquote>";
        return;
      }

      const unordered = line.match(/^[-*+]\s+(.*)$/);
      if (unordered) {
        closeParagraph();
        if (listType && listType !== "ul") closeList();
        if (!listType) {
          listType = "ul";
          html += "<ul>";
        }
        html += "<li>" + renderInline(unordered[1]) + "</li>";
        return;
      }

      const ordered = line.match(/^\d+[.)]\s+(.*)$/);
      if (ordered) {
        closeParagraph();
        if (listType && listType !== "ol") closeList();
        if (!listType) {
          listType = "ol";
          html += "<ol>";
        }
        html += "<li>" + renderInline(ordered[1]) + "</li>";
        return;
      }

      closeList();
      if (!inParagraph) {
        html += "<p>";
        inParagraph = true;
      } else {
        html += " ";
      }
      html += renderInline(line);
    });

    closeList();
    closeParagraph();

    return html.replace(/\u0000CODE(\d+)\u0000/g, function (_, index) {
      return codeBlocks[Number(index)] || "";
    });
  }

  /* -------------------------------------------------------
     Confirmable forms
     ------------------------------------------------------- */
  qsa("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.dataset.confirm)) {
        event.preventDefault();
      }
    });
  });

  /* -------------------------------------------------------
     Sidebar folders
     ------------------------------------------------------- */
  qsa("[data-folder-create-toggle]").forEach(function (button) {
    button.addEventListener("click", function () {
      const wrap = button.closest(".app-folder-create");
      const form = wrap ? wrap.querySelector(".app-folder-form") : null;
      if (!form) return;

      form.classList.toggle("d-none");
      form.classList.toggle("d-flex");

      if (!form.classList.contains("d-none")) {
        const input = form.querySelector('input[name="name"]');
        if (input) input.focus();
      }
    });
  });

  const appShell = qs(".app-shell");

  qsa("[data-folder-action]").forEach(function (button) {
    button.addEventListener("click", function () {
      const row = button.closest("[data-folder-row]");
      if (!row || !appShell) return;

      const folderId = row.dataset.folderId;
      const folderName = row.dataset.folderName;
      const action = button.dataset.folderAction;

      if (action === "subfolder") {
        const name = window.prompt("Nombre de la nueva subcarpeta", "Nueva subcarpeta");
        if (!name || !name.trim()) return;

        submitPost(appShell.dataset.createFolderUrl, {
          name: name.trim(),
          parent_id: folderId
        });
      }

      if (action === "rename") {
        const name = window.prompt("Renombrar carpeta", folderName);
        if (!name || !name.trim() || name.trim() === folderName) return;

        submitPost(withId(appShell.dataset.renameFolderUrl, folderId), {
          name: name.trim()
        });
      }

      if (action === "delete") {
        if (
          window.confirm(
            "¿Eliminar la carpeta «" +
              folderName +
              "»? Sus notas se moverán a otra carpeta."
          )
        ) {
          submitPost(withId(appShell.dataset.deleteFolderUrl, folderId), {});
        }
      }
    });
  });

  const moveNoteForm = qs("#moveNoteForm");
  qsa("[data-move-note]").forEach(function (button) {
    button.addEventListener("click", function () {
      if (!moveNoteForm || !appShell) return;
      moveNoteForm.action = withId(
        appShell.dataset.moveNoteUrl,
        button.dataset.noteId
      );
    });
  });

  /* -------------------------------------------------------
     Markdown editor (UC-03)
     ------------------------------------------------------- */
  const editorSource = qs("#editorSource");
  const editorPreview = qs("#editorPreview");
  const editorBody = qs("#editorBody");
  const titleInput = qs("#noteTitle");
  const saveStatus = qs("#saveStatus");
  const wordCount = qs("#wordCount");
  const saveUrl = titleInput ? titleInput.dataset.saveUrl : "";
  let saveTimer = null;

  function updateWordCount() {
    if (!editorSource || !wordCount) return;
    const words = editorSource.value.trim().split(/\s+/).filter(Boolean).length;
    wordCount.textContent = String(words);
  }

  function renderPreview() {
    if (!editorSource || !editorPreview) return;
    editorPreview.innerHTML = renderMarkdown(editorSource.value);
  }

  function markSaving() {
    if (!saveStatus) return;
    saveStatus.classList.remove("chip-ok");
    saveStatus.classList.add("chip-warn");
    saveStatus.innerHTML = "<b>•</b> Guardando…";
  }

  function markSaved(savedAt) {
    if (!saveStatus) return;
    saveStatus.classList.remove("chip-warn");
    saveStatus.classList.add("chip-ok");
    saveStatus.innerHTML = "<b>✓</b> Guardado · " + (savedAt || "");
  }

  function markSaveError() {
    if (!saveStatus) return;
    saveStatus.classList.remove("chip-ok");
    saveStatus.classList.add("chip-warn");
    saveStatus.innerHTML = "<b>!</b> Error al guardar";
  }

  async function persistNote() {
    if (!saveUrl || !editorSource) return;

    markSaving();

    try {
      const response = await fetch(saveUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken()
        },
        body: JSON.stringify({
          title: titleInput ? titleInput.value : "",
          content: editorSource.value
        })
      });

      if (!response.ok) throw new Error("save failed");

      const data = await response.json();
      markSaved(data.saved_at);
      if (wordCount) wordCount.textContent = String(data.words);
    } catch (error) {
      markSaveError();
    }
  }

  function scheduleSave() {
    markSaving();
    window.clearTimeout(saveTimer);
    saveTimer = window.setTimeout(persistNote, 2000);
  }

  if (editorSource) {
    renderPreview();
    updateWordCount();

    editorSource.addEventListener("input", function () {
      renderPreview();
      updateWordCount();
      scheduleSave();
    });
  }

  if (titleInput && saveUrl) {
    titleInput.addEventListener("input", scheduleSave);
  }

  qsa("[data-view]").forEach(function (button) {
    button.addEventListener("click", function () {
      if (!editorBody) return;

      qsa("[data-view]").forEach(function (other) {
        other.classList.remove("active");
      });
      button.classList.add("active");
      editorBody.dataset.view = button.dataset.view;
    });
  });

  /* -------------------------------------------------------
     AI assistant (UC-03)
     ------------------------------------------------------- */
  const aiModalElement = qs("#aiModal");
  const aiUrl = aiModalElement ? aiModalElement.dataset.aiUrl : "";
  const aiPromptWrap = qs("#aiPromptWrap");
  const aiPrompt = qs("#aiPrompt");
  const aiGenerate = qs("#aiGenerate");
  const aiStatus = qs("#aiStatus");
  const aiResult = qs("#aiResult");
  const aiInsert = qs("#aiInsert");
  const aiReplace = qs("#aiReplace");
  let aiAction = "improve";
  let aiRange = null;
  let aiBusy = false;

  function captureSelection() {
    if (!editorSource) return null;
    const start = editorSource.selectionStart;
    const end = editorSource.selectionEnd;

    if (typeof start !== "number" || start === end) return null;

    return { start: start, end: end, text: editorSource.value.slice(start, end) };
  }

  function showAiModal() {
    if (!aiModalElement || !window.bootstrap) return;
    window.bootstrap.Modal.getOrCreateInstance(aiModalElement).show();
  }

  function hideAiModal() {
    if (!aiModalElement || !window.bootstrap) return;
    window.bootstrap.Modal.getOrCreateInstance(aiModalElement).hide();
  }

  function setAiBusy(busy) {
    aiBusy = busy;

    if (aiInsert) aiInsert.disabled = busy || !aiResult.value;
    if (aiReplace) aiReplace.disabled = busy || !aiResult.value;
    if (aiGenerate) aiGenerate.disabled = busy;
  }

  async function requestAi() {
    if (!aiUrl || !aiResult || aiBusy) return;

    const prompt = aiPrompt ? aiPrompt.value.trim() : "";

    if (aiAction === "custom" && !prompt) {
      aiStatus.textContent = "Escribí una instrucción para la IA.";
      aiStatus.classList.add("error");
      return;
    }

    setAiBusy(true);
    aiStatus.classList.remove("error");
    aiStatus.textContent = "Generando…";
    aiResult.value = "";
    aiInsert.disabled = true;
    aiReplace.disabled = true;

    try {
      const response = await fetch(aiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken()
        },
        body: JSON.stringify({
          action: aiAction,
          prompt: prompt,
          selection: aiRange ? aiRange.text : ""
        })
      });

      const data = await response.json().catch(function () {
        return {};
      });

      if (!response.ok || !data.ok) {
        throw new Error(data.error || "No se pudo generar el texto.");
      }

      aiResult.value = data.text;
      aiStatus.textContent = "";
    } catch (error) {
      aiStatus.textContent =
        error.message || "No se pudo generar el texto.";
      aiStatus.classList.add("error");
    } finally {
      setAiBusy(false);
    }
  }

  qsa("[data-ai-action]").forEach(function (button) {
    button.addEventListener("click", function () {
      if (!aiModalElement) return;

      aiAction = button.dataset.aiAction || "improve";
      aiRange = captureSelection();

      aiStatus.classList.remove("error");
      aiStatus.textContent = "";
      aiResult.value = "";

      const custom = aiAction === "custom";
      aiPromptWrap.classList.toggle("d-none", !custom);
      aiGenerate.classList.toggle("d-none", !custom);

      showAiModal();

      if (custom) {
        aiPrompt.value = "";
        window.setTimeout(function () {
          aiPrompt.focus();
        }, 250);
      } else {
        requestAi();
      }
    });
  });

  if (aiGenerate) {
    aiGenerate.addEventListener("click", requestAi);
  }

  function applyAiResult(replaceAll) {
    if (!editorSource || !aiResult || !aiResult.value) return;

    const text = aiResult.value;

    if (replaceAll) {
      editorSource.value = text;
    } else {
      const start = aiRange ? aiRange.start : editorSource.selectionStart;
      const end = aiRange ? aiRange.end : editorSource.selectionEnd;

      editorSource.value =
        editorSource.value.slice(0, start) + text + editorSource.value.slice(end);
    }

    editorSource.focus();
    editorSource.dispatchEvent(new Event("input", { bubbles: true }));
    hideAiModal();
  }

  if (aiInsert) {
    aiInsert.addEventListener("click", function () {
      applyAiResult(false);
    });
  }

  if (aiReplace) {
    aiReplace.addEventListener("click", function () {
      applyAiResult(true);
    });
  }

  qsa("[data-copy-link]").forEach(function (button) {
    button.addEventListener("click", async function () {
      const original = button.innerHTML;
      try {
        await navigator.clipboard.writeText(window.location.href);
        button.innerHTML = '<i class="bi bi-check2"></i> Enlace copiado';
      } catch (error) {
        window.prompt("Copiá el enlace de la nota:", window.location.href);
      }

      window.setTimeout(function () {
        button.innerHTML = original;
      }, 1600);
    });
  });

  /* -------------------------------------------------------
     Export / import (UC-12)
     ------------------------------------------------------- */
  qsa("[data-export-format]").forEach(function (label) {
    label.addEventListener("click", function () {
      qsa("[data-export-format]").forEach(function (other) {
        other.classList.remove("selected");
      });
      label.classList.add("selected");
    });
  });

  const dropzone = qs("#importDropzone");
  const fileInput = qs("#importFiles");
  const importFileList = qs("#importFileList");
  const importButton = qs("[data-import-button]");

  function updateImportCount() {
    if (!importButton) return;
    const count = importFileList
      ? importFileList.querySelectorAll(".list-item").length
      : 0;
    importButton.textContent =
      "Importar (" + count + (count === 1 ? " archivo)" : " archivos)");
  }

  function renderImportFiles(files) {
    if (!importFileList) return;

    importFileList.innerHTML = "";

    Array.from(files || [])
      .slice(0, 10)
      .forEach(function (file) {
        const item = document.createElement("div");
        item.className = "list-item";
        item.innerHTML =
          '<span class="nm"><b></b><span></span></span>' +
          '<span class="chip chip-ok">✓</span>';

        item.querySelector("b").textContent = file.name;
        item.querySelector(".nm span").textContent =
          formatBytes(file.size) + " · listo";
        importFileList.appendChild(item);
      });

    updateImportCount();
  }

  function setImportFiles(files) {
    if (!fileInput) return;

    try {
      const transfer = new DataTransfer();
      Array.from(files || [])
        .slice(0, 10)
        .forEach(function (file) {
          transfer.items.add(file);
        });
      fileInput.files = transfer.files;
    } catch (error) {
      // Browsers without DataTransfer still submit files chosen with the picker.
    }

    renderImportFiles(fileInput.files);
  }

  if (dropzone && fileInput) {
    dropzone.addEventListener("click", function (event) {
      if (event.target === fileInput) return;
      fileInput.click();
    });

    dropzone.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        fileInput.click();
      }
    });

    ["dragenter", "dragover"].forEach(function (eventName) {
      dropzone.addEventListener(eventName, function (event) {
        event.preventDefault();
        dropzone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach(function (eventName) {
      dropzone.addEventListener(eventName, function (event) {
        event.preventDefault();
        dropzone.classList.remove("dragover");
      });
    });

    dropzone.addEventListener("drop", function (event) {
      if (event.dataTransfer && event.dataTransfer.files.length) {
        setImportFiles(event.dataTransfer.files);
      }
    });

    fileInput.addEventListener("change", function () {
      renderImportFiles(fileInput.files);
    });
  }
})();
