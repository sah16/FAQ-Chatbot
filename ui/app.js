/**
 * Groww FAQ Chatbot — Client Frontend Controller
 * Dark & Blue Theme with Scheme Sidebar & Interactive Accordions
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const chatForm = document.getElementById("chatForm");
  const queryInput = document.getElementById("queryInput");
  const sendBtn = document.getElementById("sendBtn");
  const messagesList = document.getElementById("messagesList");
  const welcomeScreen = document.getElementById("welcomeScreen");
  const clearChatBtn = document.getElementById("clearChatBtn");

  // Sidebar Elements
  const sidebar = document.getElementById("sidebar");
  const sidebarToggleBtn = document.getElementById("sidebarToggleBtn");
  const sidebarCloseBtn = document.getElementById("sidebarCloseBtn");
  const sidebarBackdrop = document.getElementById("sidebarBackdrop");
  const schemeItems = document.querySelectorAll(".scheme-item");
  const sidebarQButtons = document.querySelectorAll(".sidebar-q-btn");

  // Modal Elements
  const aboutBtn = document.getElementById("aboutBtn");
  const aboutModal = document.getElementById("aboutModal");
  const closeModalBtn = document.getElementById("closeModalBtn");
  const modalDoneBtn = document.getElementById("modalDoneBtn");

  // --- 1. Sidebar Accordion Toggle Logic ---
  schemeItems.forEach(item => {
    const toggleBtn = item.querySelector(".scheme-toggle");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        const wasActive = item.classList.contains("active");
        
        // Collapse other items
        schemeItems.forEach(si => {
          si.classList.remove("active");
          const btn = si.querySelector(".scheme-toggle");
          if (btn) btn.setAttribute("aria-expanded", "false");
        });

        // Toggle current item
        if (!wasActive) {
          item.classList.add("active");
          toggleBtn.setAttribute("aria-expanded", "true");
        }
      });
    }
  });

  // --- 2. Mobile Sidebar Open/Close ---
  function openMobileSidebar() {
    sidebar.classList.add("open");
    sidebarBackdrop.classList.add("active");
  }

  function closeMobileSidebar() {
    sidebar.classList.remove("open");
    sidebarBackdrop.classList.remove("active");
  }

  if (sidebarToggleBtn) sidebarToggleBtn.addEventListener("click", openMobileSidebar);
  if (sidebarCloseBtn) sidebarCloseBtn.addEventListener("click", closeMobileSidebar);
  if (sidebarBackdrop) sidebarBackdrop.addEventListener("click", closeMobileSidebar);

  // --- 3. Sidebar Question Buttons Click Handler ---
  sidebarQButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const query = btn.getAttribute("data-query");
      if (query) {
        closeMobileSidebar();
        submitQuery(query);
      }
    });
  });

  // --- 4. Welcome Screen Starter Chips ---
  document.querySelectorAll(".question-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const query = chip.getAttribute("data-query");
      if (query) {
        submitQuery(query);
      }
    });
  });

  // --- 5. Modal Dialog Handlers ---
  function openModal() {
    if (aboutModal) aboutModal.style.display = "flex";
  }

  function closeModal() {
    if (aboutModal) aboutModal.style.display = "none";
  }

  if (aboutBtn) aboutBtn.addEventListener("click", openModal);
  if (closeModalBtn) closeModalBtn.addEventListener("click", closeModal);
  if (modalDoneBtn) modalDoneBtn.addEventListener("click", closeModal);
  if (aboutModal) {
    aboutModal.addEventListener("click", (e) => {
      if (e.target === aboutModal) closeModal();
    });
  }

  // --- 6. New Chat / Reset History ---
  if (clearChatBtn) {
    clearChatBtn.addEventListener("click", () => {
      messagesList.innerHTML = "";
      if (welcomeScreen) {
        messagesList.appendChild(welcomeScreen);
        welcomeScreen.style.display = "flex";
      }
      queryInput.value = "";
      queryInput.focus();
    });
  }

  // --- 7. Form Submission & API Integration ---
  if (chatForm) {
    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const text = queryInput.value.trim();
      if (!text) return;
      submitQuery(text);
    });
  }

  async function submitQuery(userText) {
    // Hide welcome hero on first message
    if (welcomeScreen && welcomeScreen.style.display !== "none") {
      welcomeScreen.style.display = "none";
    }

    // Append User Message
    appendUserMessage(userText);

    // Reset Input
    queryInput.value = "";
    queryInput.disabled = true;
    sendBtn.disabled = true;

    // Show Loading Shimmer
    const loadingRow = appendLoadingIndicator();
    scrollToBottom();

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userText })
      });

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      const data = await response.json();
      
      // Remove loading indicator
      loadingRow.remove();

      // Render Assistant Response
      appendAssistantMessage(data);

    } catch (err) {
      loadingRow.remove();
      appendErrorMessage(`Error: Could not connect to Groww FAQ Chatbot API (${err.message}). Please verify the backend is running.`);
    } finally {
      queryInput.disabled = false;
      sendBtn.disabled = false;
      queryInput.focus();
      scrollToBottom();
    }
  }

  // --- 8. DOM Message Renderers ---
  function appendUserMessage(text) {
    const row = document.createElement("div");
    row.className = "message-row user-row";
    row.innerHTML = `<div class="user-bubble">${escapeHtml(text)}</div>`;
    messagesList.appendChild(row);
  }

  function appendLoadingIndicator() {
    const row = document.createElement("div");
    row.className = "message-row assistant-row";
    row.innerHTML = `
      <div class="loading-card">
        <div class="pulse-dots">
          <div class="pulse-dot"></div>
          <div class="pulse-dot"></div>
          <div class="pulse-dot"></div>
        </div>
        <span class="loading-text">Retrieving verified facts from official Groww scheme documentation...</span>
      </div>
    `;
    messagesList.appendChild(row);
    return row;
  }

  function appendAssistantMessage(data) {
    const row = document.createElement("div");
    row.className = "message-row assistant-row";

    const isRefusal = data.is_refusal;
    const card = document.createElement("div");
    card.className = `assistant-card ${isRefusal ? "refusal-card" : "factual-card"}`;

    let html = "";

    // PII Redaction Warning Banner
    if (data.pii_detected) {
      html += `
        <div class="pii-notice-badge">
          <span class="material-symbols-outlined text-[14px]">lock</span>
          <span>Sensitive PII detected and scrubbed before processing</span>
        </div>
      `;
    }

    // Refusal Tag
    if (isRefusal) {
      const intentLabel = (data.intent_category || "Refusal").toUpperCase().replace(/_/g, " ");
      html += `
        <div class="refusal-pill">
          <span class="material-symbols-outlined text-[14px]">warning</span>
          <span>Refusal Policy: ${escapeHtml(intentLabel)}</span>
        </div>
      `;
    }

    // Formatted Body Text (Markdown parse)
    const formattedText = parseMarkdown(data.response_text || "");
    html += `<div class="answer-body">${formattedText}</div>`;

    // Citations & Action Buttons
    if (!isRefusal && data.citation_url) {
      const title = data.citation_title || "Official Groww Scheme Page";
      html += `
        <div class="citation-area">
          <a href="${data.citation_url}" target="_blank" rel="noopener noreferrer" class="citation-pill" title="Open verified source on Groww">
            <span class="material-symbols-outlined text-[14px]">link</span>
            <span>Source: ${escapeHtml(title)}</span>
            <span class="material-symbols-outlined text-[12px]">open_in_new</span>
          </a>
        </div>
      `;
    } else if (isRefusal && data.educational_url) {
      html += `
        <div class="citation-area">
          <a href="${data.educational_url}" target="_blank" rel="noopener noreferrer" class="education-pill" title="Visit AMFI Investor Education">
            <span class="material-symbols-outlined text-[14px]">school</span>
            <span>AMFI Investor Education Resource ↗</span>
          </a>
        </div>
      `;
    }

    // Card Footer with Verification Date
    const updatedDate = data.last_updated || new Date().toISOString().split("T")[0];
    html += `
      <div class="card-footer">
        <span class="meta-date">
          <span class="material-symbols-outlined text-[13px]">calendar_today</span>
          <span>Last updated from sources: ${escapeHtml(updatedDate)}</span>
        </span>
      </div>
    `;

    card.innerHTML = html;
    row.appendChild(card);
    messagesList.appendChild(row);
  }

  function appendErrorMessage(msg) {
    const row = document.createElement("div");
    row.className = "message-row assistant-row";
    row.innerHTML = `
      <div class="assistant-card refusal-card">
        <div class="refusal-pill">
          <span class="material-symbols-outlined text-[14px]">error</span>
          <span>System Notice</span>
        </div>
        <div class="answer-body"><p>${escapeHtml(msg)}</p></div>
      </div>
    `;
    messagesList.appendChild(row);
  }

  function scrollToBottom() {
    window.scrollTo({
      top: document.body.scrollHeight,
      behavior: "smooth"
    });
  }

  // Basic Markdown Formatter for Assistant Responses
  function parseMarkdown(text) {
    if (!text) return "";
    
    // Escape HTML first
    let clean = escapeHtml(text);

    // Bold **text**
    clean = clean.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Masked Citations e.g. [Source: Title](url)
    clean = clean.replace(/\[Source:\s*([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, (match, title, url) => {
      return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="citation-pill"><span class="material-symbols-outlined text-[13px]">link</span> ${title} ↗</a>`;
    });

    // AMFI Links e.g. https://www.amfiindia.com/...
    clean = clean.replace(/(https?:\/\/www\.amfiindia\.com[^\s\)]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer" class="education-pill"><span class="material-symbols-outlined text-[13px]">school</span> $1 ↗</a>');

    // Paragraphs / line breaks
    const lines = clean.split("\n\n");
    return lines.map(p => `<p>${p.replace(/\n/g, "<br>")}</p>`).join("");
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }
});
