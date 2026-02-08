/**
 * Shared tooltip positioning utility.
 * Call initTooltips(iconSelector, tooltipSelector) to set up
 * hover-based tooltip positioning for any icon + nested tooltip pair.
 *
 * @param {string} iconSelector  - CSS selector for the trigger element
 * @param {string} tooltipSelector - CSS selector (relative to icon) for the tooltip element
 * @param {object} [opts] - Options
 * @param {boolean} [opts.moveToBody=true] - Move tooltip to <body> on hover for overflow safety
 */
function initTooltips(iconSelector, tooltipSelector, opts) {
    var moveToBody = (!opts || opts.moveToBody !== false);

    document.querySelectorAll(iconSelector).forEach(function (icon) {
        var tooltip = icon.querySelector(tooltipSelector);
        if (!tooltip) return;

        var inBody = false;

        icon.addEventListener('mouseenter', function () {
            var rect = icon.getBoundingClientRect();

            if (moveToBody && !inBody) {
                document.body.appendChild(tooltip);
                inBody = true;
            }

            // Make visible but transparent to measure
            tooltip.style.visibility = 'visible';
            tooltip.style.opacity = '0';
            var tr = tooltip.getBoundingClientRect();

            var vw = window.innerWidth;
            var vh = window.innerHeight;

            // Position above, centered
            var top = rect.top - tr.height - 8;
            var left = rect.left + rect.width / 2;

            // Right edge
            if (left + tr.width / 2 > vw - 10) left = vw - tr.width / 2 - 10;
            // Left edge
            if (left - tr.width / 2 < 10) left = tr.width / 2 + 10;
            // Top edge – flip below
            if (top < 10) top = rect.bottom + 8;
            // Bottom edge
            if (top + tr.height > vh - 10) {
                top = rect.top - tr.height - 8;
                if (top < 10) top = 10;
            }

            tooltip.style.top = top + 'px';
            tooltip.style.left = left + 'px';
            tooltip.style.opacity = '1';
        });

        icon.addEventListener('mouseleave', function () {
            tooltip.style.visibility = 'hidden';
            tooltip.style.opacity = '0';
            if (moveToBody && inBody) {
                icon.appendChild(tooltip);
                inBody = false;
            }
        });
    });
}
