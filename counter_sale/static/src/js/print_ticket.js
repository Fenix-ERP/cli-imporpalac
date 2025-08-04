/** @odoo-module **/

import qz from "qz-tray";
import {registry} from "@web/core/registry";

const RSVP_CDN_URL = "https://cdnjs.cloudflare.com/ajax/libs/rsvp/4.8.5/rsvp.min.js";
const QZ_TRAY_CDN_URL = "https://cdn.jsdelivr.net/npm/qz-tray@2.1.0/qz-tray.js";

async function loadScriptIfNeeded(url, globalVar) {
    if (window[globalVar] === undefined) {
        return new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = url;
            script.onload = resolve;
            script.onerror = () => reject(new Error(`Failed to load script: ${url}`));
            document.head.appendChild(script);
        });
    }
}

function configureQzApi() {
    if (qz.api.setPromiseType) {
        qz.api.setPromiseType((resolver) => new Promise(resolver));
    }

    if (qz.api.setSha256Type) {
        qz.api.setSha256Type(async (data) => {
            const hashBuffer = await crypto.subtle.digest(
                "SHA-256",
                new TextEncoder().encode(data)
            );
            return Array.from(new Uint8Array(hashBuffer))
                .map((b) => b.toString(16).padStart(2, "0"))
                .join("");
        });
    }
}

registry.category("actions").add("print_ticket_js", async (env, action) => {
    const {printerName, printData} = action.params;

    if (!printerName || !printData) {
        console.error("❌ Parámetros de impresión faltantes");
        return;
    }

    try {
        await loadScriptIfNeeded(RSVP_CDN_URL, "RSVP");
        await loadScriptIfNeeded(QZ_TRAY_CDN_URL, "qz");

        configureQzApi();
        // SetupQzSecurity();

        if (!qz.websocket.isActive()) {
            await qz.websocket.connect();
            console.log("🔌 Conexión WebSocket establecida");
        }

        const printer = await qz.printers.find(printerName);
        if (!printer) {
            throw new Error(`Impresora '${printerName}' no encontrada`);
        }

        const config = qz.configs.create(printer);
        await qz.print(config, printData);

        console.log(`✅ Ticket impreso correctamente en ${printerName}`);
    } catch (error) {
        console.error("❌ Error en el proceso de impresión:", error.message);
        throw error;
    }
});
