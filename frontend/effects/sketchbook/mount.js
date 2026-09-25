import { createSketchbookDocument } from "./sketchbookDocument.js";

function Sketchbook({ assetBaseUrl = "/sketchbook/", className = "" } = {}) {
  const root = document.createElement("div");
  root.className = `sketchbook${className ? ` ${className}` : ""}`;
  root.dataset.state = "loading";

  const frame = document.createElement("iframe");
  frame.className = "sketchbook__frame";
  frame.title = "Interactive Singapore sketchbook";
  frame.setAttribute("sandbox", "allow-scripts");
  frame.loading = "eager";
  frame.addEventListener("load", () => {
    root.dataset.state = "ready";
    frame.classList.add("is-ready");
  }, { once: true });
  frame.srcdoc = createSketchbookDocument(assetBaseUrl);

  root.append(frame);
  return root;
}

function mountWhenVisible(container) {
  let mounted = false;
  const mount = () => {
    if (mounted) return;
    mounted = true;
    container.replaceChildren(Sketchbook({ assetBaseUrl: "/sketchbook/" }));
  };

  if (!("IntersectionObserver" in window)) {
    mount();
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      observer.disconnect();
      mount();
    }
  }, { rootMargin: "180px 0px" });

  observer.observe(container);
}

const mountPoint = document.querySelector("[data-sketchbook-mount]");
if (mountPoint) mountWhenVisible(mountPoint);
