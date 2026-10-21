/* Shared theme handling: loaded in <head> so the theme is set before first paint. */
(function () {
    var root = document.documentElement;

    try {
        var saved = localStorage.getItem("theme");
        var dark = saved ? saved === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
        root.setAttribute("data-theme", dark ? "dark" : "light");
    } catch (e) {
        root.setAttribute("data-theme", "light");
    }

    document.addEventListener("DOMContentLoaded", function () {
        var btn = document.getElementById("theme-btn");
        if (!btn) return;

        function label() {
            btn.textContent = root.getAttribute("data-theme") === "dark" ? "Light" : "Dark";
        }
        label();

        btn.addEventListener("click", function () {
            var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
            root.setAttribute("data-theme", next);
            try { localStorage.setItem("theme", next); } catch (e) {}
            label();
        });
    });
})();
/* Visitor statistics (GoatCounter, no cookies) */
(function () {
    var s = document.createElement("script");
    s.async = true;
    s.src = "//gc.zgo.at/count.js";
    s.setAttribute("data-goatcounter", "https://denayahs.goatcounter.com/count");
    document.head.appendChild(s);
})();
