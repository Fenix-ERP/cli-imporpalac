/** @odoo-module **/
import {registry} from "@web/core/registry";
import {FormController} from "@web/views/form/form_controller";
import {patch} from "@web/core/utils/patch";

async function print_sale_tickets(env, action) {
    const orderId = action.params.order_id || env.model.root.resId;

    const [dispatchRes, cashRes] = await Promise.all([
        fetch(`/print/ticket_html/${orderId}/dispatch`),
        fetch(`/print/ticket_html/${orderId}/cash_register`),
    ]);

    const [htmlDispatch, htmlCash] = await Promise.all([
        dispatchRes.text(),
        cashRes.text(),
    ]);

    const buildPrintData = (html) => [
        {
            type: "pixel",
            format: "html",
            flavor: "plain",
            data: html,
        },
    ];

    const doPrint = async (printData, printerName) => {
        return env.services.action.doAction({
            type: "ir.actions.client",
            tag: "print_ticket_js",
            params: {
                printerName,
                printData,
            },
        });
    };
    const cashPrinter = "POS-80C";
    const dispatchPrinter = "POS-80C";

    await doPrint(buildPrintData(htmlCash), cashPrinter);
    await doPrint(buildPrintData(htmlCash), cashPrinter);
    await doPrint(buildPrintData(htmlDispatch), dispatchPrinter);
}

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
    },

    async afterExecuteActionButton(clickParams) {
        if (
            clickParams.type === "object" &&
            clickParams.name === "action_confirm" &&
            this.model.root.data.state === "sale"
        ) {
            await print_sale_tickets(this.env, {
                params: {order_id: this.model.root.resId},
            });
        }
    },
});
registry.category("actions").add("print_sale_order", print_sale_tickets);

registry.category("views").add("view_sale_order_counter_form", {
    ...registry.category("views").get("form"),
    Controller: FormController,
});
