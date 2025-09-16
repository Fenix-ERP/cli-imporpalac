/** @odoo-module **/
/* global qz, RSVP */
import {registry} from "@web/core/registry";

const RSVP_CDN_URL = "https://cdnjs.cloudflare.com/ajax/libs/rsvp/4.8.5/rsvp.min.js";
const QZ_TRAY_CDN_URL = "https://cdn.jsdelivr.net/npm/qz-tray@2.1.0/qz-tray.js";
const QZ_CERTIFICATE_URL = "/qz/certificate";
const QZ_SIGNATURE_URL = "/qz/sign";

// Cargar librería si no existe
async function loadScriptIfNeeded(url, globalVar) {
    debugger;
    if (window[globalVar]) return;
    return new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = url;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}
function configureQzApi() {
    debugger;
    if (!qz.api) return;

    // Forzar uso de Promises de JavaScript
    if (qz.api.setPromiseType) {
        qz.api.setPromiseType((resolver) => new Promise(resolver));
    }

    // Definir SHA-256 para QZ
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
async function setupQzSecurity() {
    qz.security.setCertificatePromise((resolve, reject) => {
        fetch(QZ_CERTIFICATE_URL)
            .then((response) => {
                if (!response.ok) {
                    throw new Error(
                        `Failed to load certificate. Status: ${response.status}`
                    );
                }
                return response.text();
            })
            .then((cert) => {
                console.log("✅ QZ Tray certificate loaded");
                resolve(cert);
            })
            .catch((err) => {
                console.error("❌ Failed to load QZ Tray certificate:", err);
                reject(err);
            });
    });

    qz.security.setSignatureAlgorithm("SHA512");

    qz.security.setSignaturePromise((toSign) => {
        return (resolve, reject) => {
            fetch(`${QZ_SIGNATURE_URL}/${encodeURIComponent(toSign)}`)
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(
                            `Signature request failed. Status: ${response.status}`
                        );
                    }
                    return response.text();
                })
                .then((signature) => {
                    resolve(signature);
                })
                .catch((err) => {
                    console.error("❌ Failed to sign data:", err);
                    reject(err);
                });
        };
    });
}

const actionRegistry = registry.category("actions");

actionRegistry.add("zebra_print_action", async (env, action) => {
    debugger;
    const zplCode = action.params.zpl_code;
    if (!zplCode) {
        alert("No hay ZPL para imprimir");
        return;
    }

    try {
        // Cargar RSVP y QZ Tray
        await loadScriptIfNeeded(RSVP_CDN_URL, "RSVP");
        await loadScriptIfNeeded(QZ_TRAY_CDN_URL, "qz");
        configureQzApi();
        await setupQzSecurity();
        if (!qz.websocket.isActive()) await qz.websocket.connect();
        debugger;
        const availablePrinters = await qz.printers.find();
        const zebraPrinter = availablePrinters.find(
            (printer) => printer === "Zebra_ZD220"
        );
        const config = qz.configs.create(zebraPrinter, {forceRaw: true});
        const data = [
            {
                type: "raw",
                format: "plain",
                data: zplCode,
            },
        ];
        await qz.print(config, data);
        console.log("✅ Impresión enviada correctamente");
    } catch (err) {
        console.error("❌ Error al imprimir:", err);
        alert("Error al imprimir: " + err.message);
        if (qz.websocket && qz.websocket.isActive()) {
            await qz.websocket.disconnect();
        }
    }
});
