/** Minimal mobile navigation for the static academic website. */
(() => {
  const button = document.querySelector(".menu-toggle");
  const nav = document.querySelector(".site-nav");

  button?.addEventListener("click", () => {
    const open = button.getAttribute("aria-expanded") === "true";
    button.setAttribute("aria-expanded", String(!open));
    nav?.classList.toggle("is-open", !open);
  });

  nav?.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      button?.setAttribute("aria-expanded", "false");
      nav.classList.remove("is-open");
    });
  });

  const year = document.querySelector("[data-year]");
  if (year) year.textContent = String(new Date().getFullYear());
})();
