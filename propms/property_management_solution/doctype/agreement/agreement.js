// Copyright (c) 2018, Aakvatech and contributors
// For license information, please see license.txt
// cur_frm.add_fetch('property', 'unit_owner', 'property_owner');

// frappe.ui.form.on('Agreement', {
// 	setup: function (frm) {
// 		// frm.set_query("lease_item", "lease_item", function () {
// 		// 	return {
// 		// 		"filters": [
// 		// 			["item_group", "=", "Agreement Items"],
// 		// 		]
// 		// 	};
// 		// });
// 		frm.set_query("property", function () {
// 			return {
// 				"filters": {
// 					"company": frm.doc.company,
// 				},
// 			};
// 		});
// 	},
// 	refresh: function (frm) {
// 		cur_frm.add_custom_button(__("Make Invoice Schedule"), function () {
// 			make_lease_invoice_schedule(cur_frm);
// 		});
// 		cur_frm.add_custom_button(__("Generate Pending Invoice"), function () {
// 			generate_pending_invoice();
// 		});
// 		cur_frm.add_custom_button(__("Make Invoice Schedule for all Agreement"), function () {
// 			getAllAgreement(cur_frm);
// 		});
// 	},
// 	onload: function (frm) {
// 		frappe.realtime.on("lease_invoice_schedule_progress", function (data) {
// 			if (data.reload && data.reload === 1) {
// 				frm.reload_doc();
// 			}
// 			if (data.progress) {
// 				let progress_bar = $(cur_frm.dashboard.progress_area).find(".progress-bar");
// 				if (progress_bar) {
// 					$(progress_bar).removeClass("progress-bar-danger").addClass("progress-bar-success progress-bar-striped");
// 					$(progress_bar).css("width", data.progress + "%");
// 				}
// 			}
// 		});
// 	}
// });

// var make_lease_invoice_schedule = function (frm) {
// 	var doc = frm.doc;
// 	frappe.call({
// 		method: "propms.property_management_solution.doctype.lease.lease.make_lease_invoice_schedule",
// 		args: { leasedoc: doc.name },
// 		callback: function () {
// 			cur_frm.reload_doc();
// 		}
// 	});
// };

// var generate_pending_invoice = function () {
// 	frappe.call({
// 		method: "propms.lease_invoice.leaseInvoiceAutoCreate",
// 		args: {},
// 		callback: function () {
// 			cur_frm.reload_doc();
// 		}
// 	});
// };

// var getAllAgreement = function () {
// 	frappe.confirm(
// 		'Are you sure to initiate this long process?',
// 		function () {
// 			frappe.call({
// 				method: "propms.property_management_solution.doctype.lease.lease.getAllAgreement",
// 				args: {},
// 				callback: function () {
// 					cur_frm.reload_doc();
// 				}
// 			});
// 		},
// 		function () {
// 			frappe.msgprint(__("Closed before starting long process!"));
// 			window.close();
// 		}
// 	)
// };

// property_management_solution/doctype/agreement/agreement.js

frappe.ui.form.on("Agreement", {
	refresh(frm) {
		// update resident count
		update_resident_count(frm);

		// only when new doc and attachments are empty
		if (frm.is_new() && !(frm.doc.attachments && frm.doc.attachments.length)) {
			let row = frm.add_child("attachments");
			row.file_name = "Signed Agreement";  // optional default
			row.file_type = "PDF";
			frm.refresh_field("attachments");
		}
		if (!frm.is_new() && frm.doc.status === "Active") {
			frm.add_custom_button("Generate Next Billing", () => {
				frappe.call({
					method: "propms.property_management_solution.doctype.agreement.agreement.generate_next_billing_manual",
					args: { agreement: frm.doc.name },
					callback: function (resp) {
						if (resp.message) {
							let { status, message } = resp.message;
							if (status === "success") {
								frappe.msgprint({
									title: "Success",
									indicator: "green",
									message: message
								});
								frm.reload_doc();
							} else {
								frappe.msgprint({
									title: "Error",
									indicator: "red",
									message: message
								});
							}
						}
					}
				});
			});

		}
	},
	validate(frm) {
		if (!frm.signed_agreement_received && frm.doc.attachments && frm.doc.attachments.length) {
			// look for Signed Agreement row

			let signed_row = frm.doc.attachments.find(row => row.file);
			console.log("signed", signed_row)
			if (signed_row) {
				frm.set_value("signed_agreement_received", 1);
			} else {
				frm.set_value("signed_agreement_received", 0);
			}
		}

		if (frm.is_new() && !frm.doc.next_period_start) {
			frm.set_value("next_period_start", frm.doc.start_date)
		}

		if (frm.is_new() && !frm.doc.next_period_end) {
			frm.set_value("next_period_end", frm.doc.end_date)
		}
	}
});

frappe.ui.form.on("File and Video Attachment Items", {
	before_attachments_remove: function (frm, cdt, cdn) {
		console.log("Before Delete")
		let row = locals[cdt][cdn];
		// If attachment_type is "Signed Agreement", stop deletion
		if (row.file_name === "Signed Agreement") {
			frappe.throw(__("You cannot delete the mandatory 'Signed Agreement' attachment."));
			return false;
		}
	}
});

frappe.ui.form.on("Agreement Resident", {
	resident_add(frm) {
		update_resident_count(frm);
	},
	resident_remove(frm) {
		update_resident_count(frm);
	},

});

function update_resident_count(frm) {
	if (frm.doc.resident) {
		frm.set_value("number_of_residents", frm.doc.resident.length);
	} else {
		frm.set_value("number_of_residents", 0);
	}
}

