// Copyright (c) 2025, Aakvatech and contributors
// For license information, please see license.txt

frappe.ui.form.on("Agreement Billing Entry", {
    refresh: function (frm) {
        if (!frm.doc.__islocal) {   // show buttons only after save
            if (frm.doc.status === "Pending" || frm.doc.status === "Sent") {

                // Send Button
                frm.add_custom_button("Send Email", function () {
                    frappe.call({
                        method: "propms.api.billing.send_billing_entry",
                        args: {
                            docname: frm.doc.name
                        },
                        callback: function (r) {
                            if (!r.exc) {
                                frappe.msgprint("Billing Entry Sent Successfully");
                                frm.reload_doc();
                            }
                        }
                    });
                },);

                // Pay Button
                frm.add_custom_button("Paid", function () {
                    frappe.call({
                        method: "propms.api.billing.pay_billing_entry",
                        args: {
                            docname: frm.doc.name
                        },
                        callback: function (r) {
                            if (!r.exc) {
                                frappe.msgprint("Payment Recorded Successfully");
                                frm.reload_doc();
                            }
                        }
                    });
                },);
            }
        }
    }
});

