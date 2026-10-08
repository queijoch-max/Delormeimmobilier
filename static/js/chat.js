/*
 * Widget de chat du site public.
 * Envoie la question en JSON à l'API Django (POST /chat/question/) et affiche la réponse.
 * Aucun framework : du JavaScript natif suffit pour ce besoin.
 */
(function () {
  const root = document.querySelector("[data-chat]");
  if (!root) return;

  const panel = root.querySelector(".chat-panel");
  const toggles = root.querySelectorAll("[data-chat-toggle]");
  const openButton = root.querySelector(".chat-toggle");
  const log = root.querySelector("[data-chat-log]");
  const form = root.querySelector("[data-chat-form]");
  const input = form.querySelector("input[name=question]");
  const submit = form.querySelector("button[type=submit]");
  const csrfToken = form.querySelector("input[name=csrfmiddlewaretoken]").value;

  function setOpen(open) {
    panel.hidden = !open;
    openButton.hidden = open;
    openButton.setAttribute("aria-expanded", String(open));
    if (open) input.focus();
  }

  toggles.forEach((button) => button.addEventListener("click", () => setOpen(panel.hidden)));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) setOpen(false);
  });

  function addMessage(text, who) {
    const p = document.createElement("p");
    p.className = `chat-msg chat-msg-${who}`;
    p.textContent = text; // textContent (et non innerHTML) : protège contre l'injection de HTML
    log.appendChild(p);
    log.scrollTop = log.scrollHeight;
    return p;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = input.value.trim();
    if (!question) return;

    addMessage(question, "user");
    input.value = "";
    submit.disabled = true;
    const pending = addMessage("…", "bot");
    pending.classList.add("chat-msg-pending");

    try {
      const response = await fetch(root.dataset.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
        body: JSON.stringify({ question, property_id: root.dataset.propertyId || null }),
      });
      const data = await response.json();
      pending.textContent = data.answer || data.error || "Une erreur est survenue.";
    } catch (error) {
      pending.textContent = "Connexion impossible. Vérifiez votre réseau et réessayez.";
    } finally {
      pending.classList.remove("chat-msg-pending");
      submit.disabled = false;
      input.focus();
    }
  });
})();
