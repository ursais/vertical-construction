def _post_init_hook(env):
    demo_budget = env.ref(
        "construction_budget_apu.demo_budget",
        raise_if_not_found=False,
    )
    demo_version = env.ref(
        "construction_budget_apu.demo_budget_version_1",
        raise_if_not_found=False,
    )
    if demo_budget and demo_version and not demo_budget.current_version_id:
        demo_budget.current_version_id = demo_version
    if demo_budget and not demo_budget.default_budget_post_id:
        expense_account = env["account.account"].search(
            [
                ("account_type", "=", "expense"),
                ("company_ids", "in", env.company.id),
            ],
            limit=1,
        )
        if expense_account:
            demo_budget.default_budget_post_id = env["account.budget.post"].create(
                {
                    "name": "Construction Costs",
                    "account_ids": [(6, 0, expense_account.ids)],
                }
            )
