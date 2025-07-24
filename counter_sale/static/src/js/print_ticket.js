/** @odoo-module **/
/* global qz */

import {registry} from "@web/core/registry";

registry.category("actions").add("print_ticket_js", async (env, action) => {
    const {printerName, printData} = action.params;

    try {
        if (typeof RSVP === "undefined") {
            await new Promise((resolve, reject) => {
                const rsvpScript = document.createElement("script");
                rsvpScript.src =
                    "https://cdnjs.cloudflare.com/ajax/libs/rsvp/4.8.5/rsvp.min.js";
                rsvpScript.onload = resolve;
                rsvpScript.onerror = reject;
                document.head.appendChild(rsvpScript);
            });
        }
        if (!window.qz) {
            await new Promise((resolve, reject) => {
                const script = document.createElement("script");
                script.src = "https://cdn.jsdelivr.net/npm/qz-tray@2.1.0/qz-tray.js";
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });
        }
        if (qz.api.setPromiseType) {
            qz.api.setPromiseType((resolver) => new Promise(resolver));
        }
        if (qz.api.setSha256Type) {
            qz.api.setSha256Type((data) => {
                return crypto.subtle
                    .digest("SHA-256", new TextEncoder().encode(data))
                    .then((hashBuffer) => {
                        const hashArray = Array.from(new Uint8Array(hashBuffer));
                        return hashArray
                            .map((b) => b.toString(16).padStart(2, "0"))
                            .join("");
                    });
            });
        }
        if (!qz.websocket.isActive()) {
            await qz.websocket.connect();
        }

        const printer = await qz.printers.find(printerName);
        const config = qz.configs.create(printer);

        await qz.print(config, printData);
        console.log("✅ Ticket impreso correctamente");
    } catch (error) {
        console.error("Error imprimiendo con QZ Tray:", error);
    }
});
