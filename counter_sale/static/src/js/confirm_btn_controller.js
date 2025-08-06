/** @odoo-module **/
import {registry} from "@web/core/registry";
import {FormController} from "@web/views/form/form_controller";
import {patch} from "@web/core/utils/patch";

async function print_sale_tickets(env, action) {
    const orderId = action.params.order_id || env.model.root.resId;

    const [dispatchRes, cashRes, printers] = await Promise.all([
        fetch(`/print/ticket_html/${orderId}/dispatch`),
        fetch(`/print/ticket_html/${orderId}/cash_register`),
        fetch("/print/imporpalac_printers"),
    ]);

    const [htmlDispatch, htmlCash, printerNames] = await Promise.all([
        dispatchRes.text(),
        cashRes.text(),
        printers.json(),
    ]);

    const {cash_printer, dispatch_printer} = printerNames;
    const cashPrinterName = cash_printer || "default-printer";
    const DispatchPrinterName = dispatch_printer || "default-printer";
    const cashPrint = {
        name: cashPrinterName,
        options: {
            jobName: `Ticket Caja Orden ${orderId}`,
            copies: 2,
        },
    };
    const dispatchPrint = {
        name: DispatchPrinterName,
        options: {
            jobName: `Ticket Despacho Orden ${orderId}`,
        },
    };

    const qz_print = async (printer, printData) => {
        return env.services.action.doAction({
            type: "ir.actions.client",
            tag: "qz_print_action",
            params: {
                printer,
                printData,
            },
        });
    };
    await qz_print(cashPrint, htmlCash);
    await qz_print(dispatchPrint, htmlDispatch);
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
