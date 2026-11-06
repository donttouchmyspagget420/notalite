(function () {
  "use strict";

  const qs = (selector, root) => (root || document).querySelector(selector);
  const qsa = (selector, root) => Array.from((root || document).querySelectorAll(selector));

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function currentTime() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, "0");
    const minutes = String(now.getMinutes()).padStart(2, "0");
    return hours + ":" + minutes;
  }

  function formatBytes(bytes) {
    if (!bytes) return "0 KB";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + " KB";
    return (bytes / 1024 / 1024).toFixed(1) + " MB";
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
     Notes list (UC-02)
     ------------------------------------------------------- */
  function refreshNoteCount() {
    const list = qs("#notesList");
    if (!list) return;

    const count = list.querySelectorAll(".note-row").length;
    const counter = qs("#noteCount");
    const empty = qs("#emptyNotes");

    if (counter) counter.textContent = String(count);
    if (empty) empty.hidden = count !== 0;
  }

  qsa("[data-new-note]").forEach(function (button) {
    button.addEventListener("click", function () {
      const list = qs("#notesList");
      const template = qs("#newNoteTemplate");
      if (!list || !template) return;

      const fragment = template.content.cloneNode(true);
      const row = fragment.querySelector(".note-row");
      const title = fragment.querySelector(".note-title");
      const meta = fragment.querySelector(".note-meta");

      const labels = {
        blank: ["Nueva nota", "Sin contenido · Inbox · ahora"],
        template: ["Nota desde plantilla", "Plantilla base · Inbox · ahora"],
        wiki: ["Nota desde wiki-link", "Creada desde un enlace [[…]] · Inbox · ahora"]
      };
      const label = labels[button.dataset.newNote] || labels.blank;

      if (title) title.textContent = label[0];
      if (meta) meta.textContent = label[1];
      if (row) row.classList.add("is-new");

      list.prepend(fragment);
      refreshNoteCount();
    });
  });

  refreshNoteCount();

  /* -------------------------------------------------------
     Sidebar folders (UC-04)
     ------------------------------------------------------- */
  qsa("[data-folder-create-toggle]").forEach(function (button) {
    button.addEventListener("click", function () {
      const wrap = button.closest(".app-folder-create");
      const form = wrap ? wrap.querySelector("[data-folder-create-form]") : null;
      if (!form) return;

      form.classList.toggle("d-none");
      form.classList.toggle("d-flex");

      if (!form.classList.contains("d-none")) {
        const input = form.querySelector("[data-folder-create-input]");
        if (input) input.focus();
      }
    });
  });

  qsa("[data-folder-create-form]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();

      const input = form.querySelector("[data-folder-create-input]");
      const wrap = form.closest(".app-folder-create");
      const list = wrap ? wrap.querySelector("[data-folder-list]") : null;
      const name = input ? input.value.trim() : "";

      if (!name || !list) return;

      const item = document.createElement("a");
      item.className = "app-navitem app-navitem-indent";
      item.href = "#";
      item.innerHTML =
        '<i class="bi bi-folder2"></i><span></span><span class="count">0</span>';
      item.querySelector("span").textContent = name;
      list.appendChild(item);

      if (input) input.value = "";
      form.classList.add("d-none");
      form.classList.remove("d-flex");
    });
  });

  function findFolderRow(sidebar) {
    return qs("[data-folder-row]", sidebar);
  }

  qsa("[data-folder-action]").forEach(function (button) {
    button.addEventListener("click", function () {
      const sidebar = button.closest(".app-sidebar-body");
      const folderRow = sidebar ? findFolderRow(sidebar) : null;
      if (!folderRow) return;

      const action = button.dataset.folderAction;

      if (action === "subfolder") {
        const name = window.prompt("Nombre de la nueva subcarpeta", "Nueva subcarpeta");
        if (!name) return;

        const item = document.createElement("a");
        item.className = "app-navitem app-navitem-indent-2";
        item.href = "#";
        item.innerHTML =
          '<i class="bi bi-folder2"></i><span></span><span class="count">0</span>';
        item.querySelector("span").textContent = name.trim();
        folderRow.insertAdjacentElement("afterend", item);
      }

      if (action === "rename") {
        const label = folderRow.querySelector(".app-navitem-link span");
        const name = window.prompt(
          "Renombrar carpeta",
          label ? label.textContent.trim() : ""
        );
        if (name && label) label.textContent = name.trim();
      }

      if (action === "move") {
        const modal = qs("#moveNoteModal");
        if (modal && window.bootstrap) {
          window.bootstrap.Modal.getOrCreateInstance(modal).show();
        } else {
          window.alert("Elegí una nota y usá «Mover» para seleccionar esta carpeta.");
        }
      }

      if (action === "delete") {
        const label = folderRow.querySelector(".app-navitem-link span");
        const name = label ? label.textContent.trim() : "esta carpeta";
        if (window.confirm("¿Eliminar la carpeta «" + name + "»?")) {
          folderRow.remove();
        }
      }
    });
  });

  let noteToMove = null;
  qsa("[data-move-note]").forEach(function (button) {
    button.addEventListener("click", function () {
      noteToMove = button.closest(".note-row");
    });
  });

  const confirmMove = qs("[data-confirm-move]");
  if (confirmMove) {
    confirmMove.addEventListener("click", function () {
      const selected = qs('input[name="targetFolder"]:checked');
      if (!noteToMove || !selected) return;

      const row = noteToMove;
      const chip = row.querySelector(".chip");
      if (chip) chip.textContent = selected.value;

      row.classList.add("is-new");
      window.setTimeout(function () {
        row.classList.remove("is-new");
      }, 400);

      const modal = qs("#moveNoteModal");
      if (modal && window.bootstrap) {
        window.bootstrap.Modal.getOrCreateInstance(modal).hide();
      }
    });
  }

  /* -------------------------------------------------------
     Tags (UC-05)
     ------------------------------------------------------- */
  const tagColors = ["blue", "amber", "green", "red", "purple"];

  qsa("[data-tag-create-form]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();

      const input = form.querySelector("[data-tag-create-input]");
      if (!input) return;

      const name = input.value.trim().replace(/^#/, "");
      if (!name) return;

      qsa("[data-tag-list]").forEach(function (list, index) {
        const item = document.createElement("a");
        const color = tagColors[(name.length + index) % tagColors.length];

        item.className = "app-navitem app-navitem-indent";
        item.href = "#";
        item.innerHTML =
          '<span class="tag-dot ' +
          color +
          '"></span><span></span><span class="count">0</span>';
        item.querySelectorAll("span")[1].textContent = name;
        list.appendChild(item);
      });

      input.value = "";
    });
  });

  qsa("[data-remove-tag]").forEach(function (button) {
    button.addEventListener("click", function () {
      const row = button.closest(".note-row");
      const tag = button.dataset.removeTag;
      if (!row || !tag) return;

      qsa(".chip-tag", row).forEach(function (chip) {
        if (chip.textContent.trim() === tag) chip.remove();
      });

      row.classList.add("is-removing");
      window.setTimeout(function () {
        row.classList.remove("is-removing");
      }, 300);
    });
  });

  /* -------------------------------------------------------
     Markdown editor (UC-03)
     ------------------------------------------------------- */
  const editorSource = qs("#editorSource");
  const editorPreview = qs("#editorPreview");
  const editorBody = qs("#editorBody");
  const saveStatus = qs("#saveStatus");
  const wordCount = qs("#wordCount");
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

  function markSaved() {
    if (!saveStatus) return;
    saveStatus.classList.remove("chip-warn");
    saveStatus.classList.add("chip-ok");
    saveStatus.innerHTML = "<b>✓</b> Guardado · " + currentTime();
  }

  if (editorSource && editorPreview) {
    renderPreview();
    updateWordCount();

    editorSource.addEventListener("input", function () {
      renderPreview();
      updateWordCount();
      markSaving();

      window.clearTimeout(saveTimer);
      saveTimer = window.setTimeout(markSaved, 2000);
    });
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
     Export / import (UC-12)
     ------------------------------------------------------- */
  qsa("[data-export-format]").forEach(function (button) {
    button.addEventListener("click", function () {
      qsa("[data-export-format]").forEach(function (other) {
        other.classList.remove("selected");
      });
      button.classList.add("selected");
    });
  });

  const exportButton = qs("[data-export-button]");
  if (exportButton) {
    exportButton.addEventListener("click", function () {
      const selected = qs("[data-export-format].selected");
      const format = selected ? selected.dataset.exportFormat : "markdown";
      const original = exportButton.innerHTML;

      exportButton.disabled = true;
      exportButton.textContent = "Exportando…";

      window.setTimeout(function () {
        exportButton.disabled = false;
        exportButton.innerHTML = original;

        const list = qs("#recentExports");
        if (!list) return;

        const item = document.createElement("div");
        item.className = "list-item";
        item.innerHTML =
          '<span class="nm"><b></b><span></span></span>' +
          '<button class="btn btn-app-ghost btn-app-sm" type="button">' +
          '<i class="bi bi-download"></i> Descargar</button>';

        item.querySelector("b").textContent =
          format === "pdf" ? "guia-rapida.pdf" : "guia-rapida.md";
        item.querySelector(".nm span").textContent = "ahora · " + currentTime();
        list.prepend(item);
      }, 700);
    });
  }

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

  function addImportFiles(files) {
    if (!importFileList) return;

    Array.from(files)
      .slice(0, 10 - importFileList.querySelectorAll(".list-item").length)
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
        addImportFiles(event.dataTransfer.files);
      }
    });

    fileInput.addEventListener("change", function () {
      if (fileInput.files && fileInput.files.length) {
        addImportFiles(fileInput.files);
      }
      fileInput.value = "";
    });
  }

  if (importButton) {
    importButton.addEventListener("click", function () {
      const count = importFileList
        ? importFileList.querySelectorAll(".list-item").length
        : 0;
      if (!count) return;

      const original = importButton.textContent;
      importButton.disabled = true;
      importButton.textContent = "Importando…";

      window.setTimeout(function () {
        importButton.disabled = false;
        importButton.textContent = original;
      }, 900);
    });
  }
})();
