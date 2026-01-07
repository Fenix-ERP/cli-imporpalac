/** @odoo-module **/

import {ListController} from "@web/views/list/list_controller";
import {onWillDestroy, onWillStart, useEffect} from "@odoo/owl";
import {patch} from "@web/core/utils/patch";

patch(ListController.prototype, {
    setup() {
        super.setup();
        this.allowedModels = [];
        this.can_refresh = false;
        this._pendingReload = false;
        this._onRefreshTreeView = null;

        onWillStart(async () => {
            const allowedModels = await fetch("/tree_view_refresh/allowed_models");
            const allowedModelsList = await allowedModels.json();
            if (!allowedModelsList.includes(this.props.resModel)) {
                return;
            }
            this.env.services.bus_service.addChannel("refresh_tree_view_channel");
            this._onRefreshTreeView = this.onRefershTreeView.bind(this);
            this.env.services.bus_service.addEventListener(
                "notification",
                this._onRefreshTreeView
            );
        });
        useEffect(
            (currentEditedRecord) => {
                if (this._previousEditedRecord && !currentEditedRecord) {
                    this._processPendingReload();
                }
                this._previousEditedRecord = currentEditedRecord;
            },
            () => [this.editedRecord]
        );
        onWillDestroy(() => {
            if (this._onRefreshTreeView) {
                this.env.services.bus_service.removeEventListener(
                    "notification",
                    this._onRefreshTreeView
                );
            }
        });
    },
    _processPendingReload() {
        setTimeout(() => {
            if (this._pendingReload && !this.editedRecord) {
                this.model.load();
                this._pendingReload = false;
            }
        }, 100);
    },
    onRefershTreeView(ev) {
        const notifications = ev.detail;
        for (const notification of notifications) {
            if (notification.type === "refresh_tree_view.notify") {
                if (this.editedRecord) {
                    this._pendingReload = true;
                    continue;
                }
                this.model.load();
            }
        }
    },
});
