/** @odoo-module **/
import { registry } from '@web/core/registry';
import { FormController } from '@web/views/form/form_controller';
import { patch } from '@web/core/utils/patch';

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
    },

    async afterExecuteActionButton(clickParams) {
        if (clickParams.type === 'object' && clickParams.name === 'action_confirm' && this.model.root.data.state === 'sale') {
            const orderId = this.model.root.resId;
            const cashRegister = await fetch(`/print/ticket_html/${orderId}/cash_register`);
            const html = await cashRegister.text();
            const printData = [{
                type: 'pixel',
                format: 'html',
                flavor: 'plain',
                data: html
            }];
            this.env.services.action.doAction({
                type: 'ir.actions.client',
                tag: 'print_ticket_js',
                params: {
                    printerName: "POS-80",
                    printData: printData,
                },
            });
        }
    },
});

registry.category('views').add('view_sale_order_counter_form', {
    ...registry.category('views').get('form'),
    Controller: FormController,
});
