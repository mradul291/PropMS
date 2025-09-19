# -*- coding: utf-8 -*-
# Copyright (c) 2018, Aakvatech and contributors
# For license information, pagreement see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, today, getdate, add_months, get_datetime, now
from frappe.utils import add_days, get_first_day, get_last_day, add_months, today

class Agreement(Document):  
    def on_submit(self):
        
        try:
            if (
                get_datetime(self.start_date)
                <= get_datetime(now())
                <= get_datetime(add_months(self.end_date, -3))
            ):
                frappe.db.set_value("Property", self.property, "status", "On Agreement") 
                frappe.msgprint("Property set to On Agreement")  
            if (
                get_datetime(add_months(self.end_date, -3))
                <= get_datetime(now())
                <= get_datetime(add_months(self.end_date, 3))
            ):
                frappe.db.set_value(
                    "Property", self.property, "status", "Off Agreement in 3 Months" 
                )
                frappe.msgprint("Property set to Off Agreement in 3 Months")
        except Exception as e:
            app_error_log(frappe.session.user, str(e))

    def on_update(self):
        # Check if status changed to Active
        if self.status == "Active" and self.has_value_changed("status"):
            if self.room:
                # Validate room availability before activating
                is_available = frappe.db.get_value("Room", self.room, "is_available")
                if not is_available:
                    frappe.throw(f"Room {self.room} is unavailable. Cannot activate this agreement for this Room.")

                # Mark room as unavailable
                frappe.db.set_value("Room", self.room, "is_available", 0)

        # If status changed to Terminated / Ended / Cancelled → free the room
        elif self.status in ["Terminated", "Ended", "Cancelled"] and self.has_value_changed("status"):
            if self.room:
                frappe.db.set_value("Room", self.room, "is_available", 1)

    def validate(self):
        # keep resident count in sync
        
        # Validate attachments if status = Activate
        print("self", self.signed_agreement_received)
        if self.status == "Activate" and not self.attachments and self.signed_agreement_received:
            frappe.throw("To activate the Agreement, please attach at least one Signed Agreement in Attachments.")

    # property_management_solution/doctype/agreement/agreement.py

    def generate_next_billing(self):
        """Generate billing entry if due"""

        if self.status != "Active":
            return "Agreement is not Active. Billing skipped."

        if not self.next_period_start:
            # Initialize on first run
            self.next_period_start = self.start_date

        # Check if it's time to generate billing
        if getdate(today()) < add_days(self.next_period_start, -1 * (self.days_to_invoice_in_advance or 0)):
            return "Billing already generated for the current cycle."

        # Compute period
        period_start = self.next_period_start
        period_end, period_length = self.compute_period(period_start)

        # Calculate amount
        daily_rate = self.fee_amount / period_length
        amount = daily_rate * period_length

        # Create billing entry
        billing_entry = frappe.get_doc({
            "doctype": "Agreement Billing Entry",
            "agreement": self.name,
            "period_start": period_start,
            "period_end": period_end,
            "amount": amount,
            "status": "Pending",
            "posting_date": today(),
            "due_date": add_days(today(), 7)
        })
        billing_entry.insert(ignore_permissions=True)

        # Update Agreement
        self.last_billing_entry_date = today()
        self.next_period_start = add_days(period_end, 1)
        self.next_period_end = self.compute_period(self.next_period_start)[0]
        self.save(ignore_permissions=True)

        return f"Billing Entry created for period {period_start} to {period_end}."

    def compute_period(self, start_date):
        """Return (end_date, length_in_days) based on frequency"""
        if self.frequency == "Week":
            end_date = add_days(start_date, 6)
            return end_date, 7
        elif self.frequency == "Fortnight":
            end_date = add_days(start_date, 13)
            return end_date, 14
        elif self.frequency == "Month":
            end_date = add_days(add_months(start_date, 1), -1)
            length = (end_date - start_date).days + 1
            return end_date, length
        else:
            frappe.throw("Unsupported frequency")

@frappe.whitelist()
def generate_next_billing_manual(agreement):
    try:
        doc = frappe.get_doc("Agreement", agreement)
        result = doc.generate_next_billing()
        return {"status": "success", "message": result or "Billing generated successfully."}
    except Exception as e:
        frappe.log_error(title="Billing Generation Failed", message=frappe.get_traceback())
        return {"status": "error", "message": f"Billing generation failed: {str(e)}"}

def app_error_log(user, error_message):
    frappe.log_error(
        title=f"Error by {user}",
        message=error_message
    )
    
# @frappe.whitelist()
# def getAllAgreement():
#     # Below is temporarily created to manually run through all agreement and refresh agreement invoice schedule. Hardcoded to start from 1st Jan 2020.
#     frappe.msgprint(
#         "The task of making agreement invoice schedule for all users has been sent for background processing."
#     )
#     invoice_start_date = frappe.db.get_single_value(
#         "Property Management Settings", "invoice_start_date"
#     )
#     agreement_list = frappe.get_all(
#         "Agreement", filters={"end_date": (">=", invoice_start_date)}, fields=["name"] 
#     )
#     # frappe.msgprint("Working on agreement_list" + str(agreement_list))
#     agreement_list_len = len(agreement_list)
#     frappe.msgprint("Total number of agreement to be processed is " + str(agreement_list_len))
#     for agreement in agreement_list:
#         make_agreement_invoice_schedule(agreement.name)


# # def on_update(self):
# @frappe.whitelist()
# def make_agreement_invoice_schedule(agreementdoc):
#     # frappe.msgprint("This is the parameter passed: " + str(agreementdoc))
#     agreement = frappe.get_doc("Agreement", str(agreementdoc)) 
#     try:
#         # Delete unnecessary records after agreement end date
#         agreement_invoice_schedule_list = frappe.get_list(
#             "Agreement Invoice Schedule",   
#             fields=[
#                 "name",
#                 "parent",
#                 "agreement_item",
#                 "invoice_number",
#                 "date_to_invoice",
#             ],
#             filters={"parent": agreement.name, "date_to_invoice": (">", agreement.end_date)},
#         )
#         for agreement_invoice_schedule in agreement_invoice_schedule_list:
#             frappe.delete_doc("Agreement Invoice Schedule", agreement_invoice_schedule.name) 
#         # Only process agreement that items and is current
#         if len(agreement.agreement_item) >= 1 and agreement.end_date >= getdate(today()):
#             # Clean up records that are no longer required, i.e. of unnecessary agreement items and unnecessary dates
#             # Records before Invoice Start Date
#             invoice_start_date = frappe.db.get_single_value(
#                 "Property Management Settings", "invoice_start_date"
#             )
#             agreement_invoice_schedule_list = frappe.get_list(
#                 "Agreement Invoice Schedule", 
#                 fields=["name", "parent", "invoice_number", "date_to_invoice"],
#                 filters={
#                     "parent": agreement.name,
#                     "date_to_invoice": ("<", invoice_start_date),
#                 },
#             )
#             # frappe.msgprint("Records before Invoice Start Date " + str(agreement_invoice_schedule_list))
#             for agreement_invoice_schedule in agreement_invoice_schedule_list:
#                 # frappe.msgprint("Deleting Record before Invoice Start Date " + str(invoice_start_date) + str(agreement_invoice_schedule.name))
#                 frappe.delete_doc("Agreement Invoice Schedule", agreement_invoice_schedule.name) 
#             # Records of agreement_items that no longer existing in agreement.agreement_item
#             agreement_invoice_schedule_list = frappe.get_list(
#                 "Agreement Invoice Schedule", 
#                 fields=[
#                     "name",
#                     "parent",
#                     "agreement_item",
#                     "invoice_number",
#                     "date_to_invoice",
#                 ],
#                 filters={"parent": agreement.name},
#             )
#             agreement_items_list = frappe.get_list(
#                 "Agreement Item", 
#                 fields=["name", "parent", "agreement_item"],
#                 filters={"parent": agreement.name},
#             )
#             # Create list of agreement items that are part of agreement.agreement_item
#             agreement_item_name_list = [
#                 agreement_item["agreement_item"] for agreement_item in agreement_items_list
#             ]
#             # frappe.msgprint(str(agreement_item_list))
#             for agreement_invoice_schedule in agreement_invoice_schedule_list:
#                 if agreement_invoice_schedule.agreement_item not in agreement_item_name_list:
#                     # frappe.msgprint("This agreement item will be removed from invoice schedule " + str(agreement_invoice_schedule.agreement_item))
#                     frappe.delete_doc(
#                         "Agreement Invoice Schedule", agreement_invoice_schedule.name 
#                     )
#             item_invoice_frequency = {
#                 "Monthly": 1.00,  # .00 to make it float type
#                 "Bi-Monthly": 2.00,
#                 "Quarterly": 3.00,
#                 "6 months": 6.00,
#                 "Annually": 12.00,
#             }
#             idx = 1
#             for item in agreement.agreement_item:
#                 # frappe.msgprint("Agreement item being processed: " + str(item.agreement_item))
#                 agreement_invoice_schedule_list = frappe.get_all(
#                     "Agreement Invoice Schedule", 
#                     fields=[
#                         "name",
#                         "parent",
#                         "agreement_item",
#                         "qty",
#                         "invoice_number",
#                         "date_to_invoice",
#                     ],
#                     filters={"parent": agreement.name, "agreement_item": item.agreement_item},
#                     order_by="date_to_invoice",
#                 )
#                 # frappe.msgprint(str(agreement_invoice_schedule_list))
#                 # Get the latest item frequency incase agreement was changed.
#                 frequency_factor = item_invoice_frequency.get(
#                     item.frequency, "Invalid frequency"
#                 )
#                 # frappe.msgprint("Next Invoice date calculated: " + str(invoice_date))
#                 if frequency_factor == "Invalid frequency":
#                     message = (
#                         "Invalid frequency: "
#                         + str(item.frequency)
#                         + " for "
#                         + str(agreementdoc)
#                         + " not found. Contact the developers!"
#                     )
#                     frappe.log_error("Frequency incorrect", message)
#                     break
#                 invoice_qty = float(frequency_factor)
#                 end_date = agreement.end_date
#                 invoice_date = agreement.start_date
#                 # Find out the first invoice date on or after Invoice Start Date process.
#                 while end_date >= invoice_date and invoice_date < invoice_start_date:
#                     invoice_period_end = add_days(
#                         add_months(invoice_date, frequency_factor), -1
#                     )
#                     # Set invoice_Qty as appropriate fraction of frequency_factor
#                     if invoice_period_end > end_date:
#                         invoice_qty = getDateMonthDiff(invoice_date, end_date, 1)
#                         # frappe.msgprint("Invoice quantity corrected as " + str(invoice_qty))
#                     invoice_date = add_days(invoice_period_end, 1)
#                 # If there is no agreement_invoice_schedule_list found, i.e. it is fresh new list to be created
#                 if not agreement_invoice_schedule_list:
#                     while end_date >= invoice_date:
#                         invoice_period_end = add_days(
#                             add_months(invoice_date, frequency_factor), -1
#                         )
#                         # frappe.msgprint("Invoice period end: " + str(invoice_period_end) + "--- Invoice Date: " + str(invoice_date))
#                         # frappe.msgprint("End Date: " + str(end_date))
#                         # set invoice_Qty as appropriate fraction of frequency_factor
#                         if invoice_period_end > end_date:
#                             invoice_qty = getDateMonthDiff(invoice_date, end_date, 1)
#                             # frappe.msgprint("Invoice quantity corrected as " + str(invoice_qty))
#                         # frappe.msgprint("Making Fresh Invoice Schedule for " + str(invoice_date)
#                         # 	+ ", Quantity calculated: " + str(invoice_qty))
#                         makeInvoiceSchedule(
#                             invoice_date,
#                             item.agreement_item,
#                             item.paid_by,
#                             item.agreement_item,
#                             agreement.name,
#                             invoice_qty,
#                             item.amount,
#                             idx,
#                             item.currency_code,
#                             item.witholding_tax,
#                             agreement.days_to_invoice_in_advance,
#                             item.invoice_item_group,
#                             item.document_type,
#                         )
#                         idx += 1
#                         invoice_date = add_days(invoice_period_end, 1)
#                 for agreement_invoice_schedule in agreement_invoice_schedule_list:
#                     # frappe.msgprint("Upon entering agreement_invoice_schedule_list - Date to invoice: " + str(agreement_invoice_schedule.date_to_invoice)
#                     # 	+ " and invoice date to process is " + str(invoice_date))
#                     if not (agreement_invoice_schedule.schedule_start_date):
#                         agreement_invoice_schedule.schedule_start_date = (
#                             agreement_invoice_schedule.date_to_invoice
#                         )
#                     while (
#                         end_date >= invoice_date
#                         and agreement_invoice_schedule.schedule_start_date > invoice_date
#                     ):
#                         invoice_period_end = add_days(
#                             add_months(invoice_date, frequency_factor), -1
#                         )
#                         # frappe.msgprint("Upon entering Invoice period end: " + str(invoice_period_end) + "--- Invoice Date: " + str(invoice_date))
#                         # frappe.msgprint("End Date: " + str(end_date))
#                         # set invoice_Qty as appropriate fraction of frequency_factor
#                         if invoice_period_end > end_date:
#                             invoice_qty = getDateMonthDiff(invoice_date, end_date, 1)
#                             # frappe.msgprint("Invoice quantity corrected as " + str(invoice_qty))
#                         # frappe.msgprint("Making Pre Invoice Schedule for " + str(invoice_date) + ", Quantity calculated: " + str(invoice_qty))
#                         makeInvoiceSchedule(
#                             invoice_date,
#                             item.agreement_item,
#                             item.paid_by,
#                             item.agreement_item,
#                             agreement.name,
#                             invoice_qty,
#                             item.amount,
#                             idx,
#                             item.currency_code,
#                             item.witholding_tax,
#                             agreement.days_to_invoice_in_advance,
#                             item.invoice_item_group,
#                             item.document_type,
#                         )
#                         idx += 1
#                         invoice_date = add_days(invoice_period_end, 1)
#                     # frappe.msgprint(str(agreement_invoice_schedule))
#                     # If the record already exists and invoice is generated
#                     if (
#                         agreement_invoice_schedule.invoice_number is not None
#                         and agreement_invoice_schedule.invoice_number != ""
#                     ):
#                         # frappe.msgprint("Agreement Invoice Schedule retained: " + agreement_invoice_schedule.name
#                         # 	+ " for invoice number: " + str(agreement_invoice_schedule.invoice_number)
#                         # 	+ " dated " + str(agreement_invoice_schedule.date_to_invoice)
#                         # )
#                         # Set months as rounded up by 1 if the month is a fraction (last invoice for the agreement item already created).
#                         # Above needed to escape from infinite loop of rounded down date and therefore never reaching end of the agreement.
#                         if agreement_invoice_schedule.qty != round(
#                             agreement_invoice_schedule.qty, 0
#                         ):
#                             add_months_value = round(agreement_invoice_schedule.qty, 0) + 1
#                         else:
#                             add_months_value = agreement_invoice_schedule.qty
#                         # frappe.msgprint("Add Months Value" + str(add_months_value) + " due to qty = " + str(agreement_invoice_schedule.qty))
#                         invoice_date = add_months(
#                             agreement_invoice_schedule.schedule_start_date, add_months_value
#                         )
#                         # Set sequence to show it on the top
#                         frappe.db.set_value(
#                             "Agreement Invoice Schedule", 
#                             agreement_invoice_schedule.name,
#                             "idx",
#                             idx,
#                         )
#                         idx += 1
#                     # If the invoice is not created
#                     else:
#                         # frappe.msgprint("Deleting schedule :" + agreement_invoice_schedule.name + " dated: " + str(agreement_invoice_schedule.date_to_invoice) + " for " + str(agreement_invoice_schedule.agreement_item))
#                         frappe.delete_doc(
#                             "Agreement Invoice Schedule", agreement_invoice_schedule.name 
#                         )
#                 # frappe.msgprint("first invoice_date: " + str(invoice_date), "Agreement Invoice Schedule")
#                 while end_date >= invoice_date:
#                     invoice_period_end = add_days(
#                         add_months(invoice_date, frequency_factor), -1
#                     )
#                     # frappe.msgprint("Invoice period end: " + str(invoice_period_end) + "--- Invoice Date: " + str(invoice_date))
#                     # frappe.msgprint("End Date: " + str(end_date))
#                     # set invoice_Qty as appropriate fraction of frequency_factor
#                     if invoice_period_end > end_date:
#                         invoice_qty = getDateMonthDiff(invoice_date, end_date, 1)
#                         # frappe.msgprint("Invoice quantity corrected as " + str(invoice_qty))
#                     # frappe.msgprint("Making Post Invoice Schedule for " + str(invoice_date) + ", Quantity calculated: " + str(invoice_qty))
#                     makeInvoiceSchedule(
#                         invoice_date,
#                         item.agreement_item,
#                         item.paid_by,
#                         item.agreement_item,
#                         agreement.name,
#                         invoice_qty,
#                         item.amount,
#                         idx,
#                         item.currency_code,
#                         item.witholding_tax,
#                         agreement.days_to_invoice_in_advance,
#                         item.invoice_item_group,
#                         item.document_type,
#                     )
#                     idx += 1
#                     invoice_date = add_days(invoice_period_end, 1)

#         frappe.msgprint("Completed making of invoice schedule.")

#     except Exception as e:
#         frappe.msgprint("Exception error! Check app error log.")
#         app_error_log(frappe.session.user, str(e))
