from odoo import models


class ConstructionBudgetXlsxReport(models.AbstractModel):
    _name = "report.construction_budget_apu.budget_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Construction Budget XLSX Report"

    def generate_xlsx_report(self, workbook, data, budgets):
        sheet = workbook.add_worksheet("Budget")
        header = workbook.add_format({"bold": True, "bg_color": "#D9E1F2"})
        money = workbook.add_format({"num_format": "#,##0.00"})
        row = 0
        sheet.write_row(
            row,
            0,
            [
                "Budget",
                "Project",
                "Version",
                "Chapter",
                "Item Code",
                "Description",
                "Qty",
                "Unit Price",
                "Subtotal",
            ],
            header,
        )
        row += 1
        for budget in budgets:
            version = budget.current_version_id or budget.approved_version_id
            if not version:
                continue
            for line in version.line_ids.sorted(
                lambda line: (line.chapter_id.sequence, line.sequence)
            ):
                sheet.write_row(
                    row,
                    0,
                    [
                        budget.name,
                        budget.project_id.name,
                        version.display_name,
                        line.chapter_id.display_name,
                        line.code or "",
                        line.name,
                        line.quantity,
                        line.unit_price,
                        line.subtotal,
                    ],
                )
                sheet.write_number(row, 7, line.unit_price, money)
                sheet.write_number(row, 8, line.subtotal, money)
                row += 1
        sheet.set_column(0, 8, 18)
