/* ============================================================
   BuildPath — main.js
   Small vanilla JS interactions, same pattern as ProjectPilot AI.
   ============================================================ */

document.addEventListener("DOMContentLoaded", function () {

    // Auto-dismiss flash messages after 4 seconds
    const flashMessages = document.querySelectorAll(".flash");
    flashMessages.forEach(function (flash) {
        setTimeout(function () {
            flash.style.transition = "opacity 0.5s ease";
            flash.style.opacity = "0";
            setTimeout(function () { flash.remove(); }, 500);
        }, 4000);
    });

});
