/** @odoo-module **/

import {ListController} from "@web/views/list/list_controller";
import {onWillDestroy} from "@odoo/owl";
import {patch} from "@web/core/utils/patch";

patch(ListController.prototype, {
    setup() {
        super.setup();
        const channel = JSON.stringify([
            this.env.services.bus_service.dbname,
            "stock.picking",
            "reload",
        ]);
        this.env.services.bus_service.addChannel(channel);
        const onRefershTreeView = this.onRefershTreeView.bind(this);
        this.env.services.bus_service.addEventListener(
            "notification",
            onRefershTreeView
        );
        onWillDestroy(() => {
            this.env.services.bus_service.removeEventListener(
                "notification",
                onRefershTreeView
            );
        });
    },
    onRefershTreeView(ev) {
        const notifications = ev.detail;
        for (const notification of notifications) {
            if (notification.type === "tree_view_refresh") this.model.load();
        }
    },
});
