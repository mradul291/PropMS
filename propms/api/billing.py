import frappe

@frappe.whitelist()
def send_billing_entry(docname):
    doc = frappe.get_doc("Agreement Billing Entry", docname)
    if doc.status not in ["Pending", "Sent"]:
        frappe.throw("Only Pending or Sent entries can be re-sent")
    # your email/notification logic here
    doc.status = "Sent"
    doc.save()
    frappe.db.commit()
    return {"status": "ok"}

@frappe.whitelist()
def pay_billing_entry(docname):
    doc = frappe.get_doc("Agreement Billing Entry", docname)
    if doc.status in ["Paid", "Cancelled"]:
        frappe.throw("This entry cannot be paid")
    # your payment handling logic here
    doc.status = "Paid"
    doc.save()
    frappe.db.commit()
    return {"status": "ok"}