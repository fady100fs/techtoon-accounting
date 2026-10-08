# pages/9_📚_شجرة_الحسابات.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar, queue_state_updates, can_modify
render_sidebar()

import streamlit as st
import pandas as pd
import unicodedata
from sqlalchemy import func
from database import SessionLocal
import models
from models import AccountType, Account, Party, CashBox, ExpenseCategory
from auth_required import require_login

current_user = require_login()

st.set_page_config(page_title="شجرة الحسابات", page_icon="📚", layout="wide")
st.title("📚 إدارة شجرة الحسابات")

try:
    from keyboard_nav import enable_enter_navigation, add_enter_hint
    enable_enter_navigation()
    add_enter_hint()
except Exception:
    pass

db = SessionLocal()


# ==========================================
# ⭐ خريطة أسماء الصفحات (للانتقال المباشر)
# ==========================================
PAGE_PATHS = {
    "expenses":     "pages/22_💸_المصروفات.py",
    "cash_boxes":   "pages/19_🏦_الخزائن.py",
    "items":        "pages/2_📦_الأصناف.py",
    "parties":      "pages/3_👥_عملاء وموردين.py",
    "invoices":     "pages/6_📋_فهرس_الفواتير.py",
    "payments":     "pages/8_💰_المدفوعات.py",
    "fixed_assets": "pages/24__الأصول_الثابتة.py",
    "loans":        "pages/26_💼_إدارة_القروض.py",
    "cost_centers": "pages/30_🏢_مراكز_التكلفة.py",
    "categories":   "pages/20_🗂️_التصنيفات.py",
}


PAGE_NAME_MAP = {
    "expenses":     "💸 حركات الخزينة",
    "cash_boxes":   "🏦 الخزائن",
    "items":        "📦 الأصناف",
    "parties":      "👥 عملاء وموردين",
    "invoices":     "📋 فهرس الفواتير",
    "payments":     "💰 المدفوعات",
    "fixed_assets": "🏢 الأصول الثابتة",
    "loans":        "💼 إدارة القروض",
    "cost_centers": "🏢 مراكز التكلفة",
    "categories":   "🗂️ التصنيفات",
}


def _goto_page(target_key, record_id=None, extra=None):
    """
    محاولات متعددة للانتقال (تعمل مع أسماء ملفات فيها Emoji/عربي)
    + بديل يدوي عند الفشل.
    """
    # 1) حفظ البيانات
    st.session_state[f"_from_accounts_to_{target_key}"] = True
    if record_id is not None:
        st.session_state[f"_open_{target_key}_id"] = record_id
    if extra:
        for k, v in extra.items():
            st.session_state[k] = v

    path = PAGE_PATHS.get(target_key, "")
    if not path:
        st.error(f"⚠️ لا يوجد مسار معرّف للصفحة: {target_key}")
        return

    # 2) محاولة 1: المسار الأصلي
    try:
        st.switch_page(path)
        return
    except Exception:
        pass

    # 3) محاولة 2: Unicode NFC normalization
    try:
        normalized = unicodedata.normalize("NFC", path)
        st.switch_page(normalized)
        return
    except Exception:
        pass

    # 4) محاولة 3: بدون "pages/"
    try:
        short_path = path.replace("pages/", "").replace("pages\\", "")
        st.switch_page(short_path)
        return
    except Exception:
        pass

    # 5) محاولة 4: باستخدام Path
    try:
        from pathlib import Path as _P
        p = _P(path)
        st.switch_page(str(p))
        return
    except Exception:
        pass

    # 6) كل المحاولات فشلت → رسالة يدوية
    page_name = PAGE_NAME_MAP.get(target_key, target_key)
    st.success("✅ تم تفعيل الفلتر بنجاح!")
    st.warning(
        f"⚠️ **انتقل يدوياً** من القائمة الجانبية إلى: **{page_name}**"
    )
    st.caption("💡 الفلتر محفوظ وسيُطبّق تلقائياً عند فتح الصفحة.")


# ==========================================
# دوال مساعدة
# ==========================================
def _account_usage(account_id):
    """يرجع dict بعدد السجلات المرتبطة بالحساب (شامل)."""
    usage = {
        "sub_accounts": 0,
        "journal_lines": 0,
        "parties": 0,
        "cash_boxes": 0,
        "expense_categories": 0,
        "expenses": 0,
        "payments": 0,
        "invoices": 0,
        "cash_transfers": 0,
        "items_inventory": 0,
        "items_cogs": 0,
        "items_revenue": 0,
        "fixed_assets": 0,
        "loans": 0,
        "cost_centers": 0,
        "budgets": 0,
    }

    usage["sub_accounts"] = db.query(Account).filter(
        Account.parent_id == account_id
    ).count()

    usage["journal_lines"] = db.query(models.JournalLine).filter(
        models.JournalLine.account_id == account_id
    ).count()

    party = db.query(Party).filter(Party.account_id == account_id).first()
    usage["parties"] = db.query(Party).filter(Party.account_id == account_id).count()

    if party:
        usage["invoices"] = db.query(models.Invoice).filter(
            models.Invoice.party_id == party.id
        ).count()
        usage["payments"] = db.query(models.Payment).filter(
            models.Payment.party_id == party.id
        ).count()

    usage["cash_boxes"] = db.query(CashBox).filter(
        CashBox.account_id == account_id
    ).count()

    cats = db.query(ExpenseCategory).filter(
        ExpenseCategory.account_id == account_id
    ).all()
    usage["expense_categories"] = len(cats)
    if cats:
        cat_ids = [c.id for c in cats]
        usage["expenses"] = db.query(models.Expense).filter(
            models.Expense.category_id.in_(cat_ids)
        ).count()

    usage["items_inventory"] = db.query(models.Item).filter(
        models.Item.inventory_account_id == account_id
    ).count()
    usage["items_cogs"] = db.query(models.Item).filter(
        models.Item.cogs_account_id == account_id
    ).count()
    usage["items_revenue"] = db.query(models.Item).filter(
        models.Item.revenue_account_id == account_id
    ).count()

    if usage["cash_boxes"] > 0:
        cashbox_ids = [
            b.id for b in db.query(CashBox).filter(
                CashBox.account_id == account_id
            ).all()
        ]
        if cashbox_ids:
            try:
                usage["cash_transfers"] = db.query(models.CashTransfer).filter(
                    (models.CashTransfer.from_cash_box_id.in_(cashbox_ids)) |
                    (models.CashTransfer.to_cash_box_id.in_(cashbox_ids))
                ).count()
            except Exception:
                pass

    try:
        if hasattr(models.FixedAsset, "account_id"):
            usage["fixed_assets"] = db.query(models.FixedAsset).filter(
                models.FixedAsset.account_id == account_id
            ).count()
    except Exception:
        pass

    try:
        if hasattr(models.Loan, "account_id"):
            usage["loans"] = db.query(models.Loan).filter(
                models.Loan.account_id == account_id
            ).count()
    except Exception:
        pass

    try:
        if hasattr(models.CostCenter, "account_id"):
            usage["cost_centers"] = db.query(models.CostCenter).filter(
                models.CostCenter.account_id == account_id
            ).count()
    except Exception:
        pass

    try:
        if hasattr(models.Budget, "account_id"):
            usage["budgets"] = db.query(models.Budget).filter(
                models.Budget.account_id == account_id
            ).count()
    except Exception:
        pass

    return usage


def _is_used(usage):
    return any(v > 0 for v in usage.values())


def _balance_for(account_id):
    debit_total = float(db.query(func.sum(models.JournalLine.debit)).filter(
        models.JournalLine.account_id == account_id
    ).scalar() or 0)
    credit_total = float(db.query(func.sum(models.JournalLine.credit)).filter(
        models.JournalLine.account_id == account_id
    ).scalar() or 0)
    return debit_total, credit_total, debit_total - credit_total


def _flatten_tree(all_accounts, parent_id=None, depth=0):
    children = sorted(
        [a for a in all_accounts if a.parent_id == parent_id],
        key=lambda x: x.code,
    )
    rows = []
    for child in children:
        rows.append((child, depth))
        rows.extend(_flatten_tree(all_accounts, child.id, depth + 1))
    return rows


# ==========================================
# التبويبات
# ==========================================
tab1, tab2 = st.tabs(["➕ إضافة حساب جديد", "🌳 عرض شجرة الحسابات"])


# ==========================================
# تبويب 1: إضافة حساب جديد
# ==========================================
with tab1:
    st.subheader("➕ إضافة حساب جديد")
    st.caption("💡 بعد الحفظ، الحقول هتتفرّغ تلقائيًا عشان تقدر تدخل حساب تاني فورًا.")

    account_type = st.selectbox(
        "نوع الحساب:",
        options=[acc_type.value for acc_type in AccountType],
        key="new_acc_type",
    )

    parent_accounts = db.query(Account).filter(
        Account.type == AccountType(account_type)
    ).order_by(Account.code).all()

    parent_options = {"بدون (حساب رئيسي)": None}
    for acc in parent_accounts:
        parent_options[f"{acc.code} - {acc.name}"] = acc.id

    selected_parent = st.selectbox(
        "الحساب الأب:",
        options=list(parent_options.values()),
        format_func=lambda x: next(
            (k for k, v in parent_options.items() if v == x), "بدون"
        ),
        key="new_acc_parent",
    )

    code = st.text_input("كود الحساب:", placeholder="مثال: 1103", key="new_acc_code")
    name = st.text_input("اسم الحساب:", placeholder="مثال: صندوق فرعي", key="new_acc_name")

    if st.button("💾 حفظ الحساب", type="primary", use_container_width=True):
        if not code or not name:
            st.error("❌ يرجى ملء كود واسم الحساب.")
        else:
            try:
                existing = db.query(Account).filter(Account.code == code.strip()).first()
                if existing:
                    st.error(f"❌ الكود {code} مستخدم بالفعل في الحساب '{existing.name}'.")
                else:
                    new_account = Account(
                        code=code.strip(),
                        name=name.strip(),
                        type=AccountType(account_type),
                        parent_id=selected_parent,
                    )
                    db.add(new_account)
                    db.commit()

                    st.success(f"✅ تم إضافة الحساب '{name}' بنجاح!")
                    st.balloons()

                    queue_state_updates(
                        delete_keys=("new_acc_code", "new_acc_name", "new_acc_parent"),
                        set_values={
                            "new_acc_type": AccountType.ASSET.value,
                            "new_acc_parent": None,
                        },
                    )
                    st.rerun()
            except Exception as e:
                db.rollback()
                st.error(f"❌ خطأ: {e}")


# ==========================================
# تبويب 2: عرض شجرة الحسابات + تعديل/حذف
# ==========================================
with tab2:
    st.subheader("🌳 شجرة الحسابات")

    all_accounts = db.query(Account).order_by(Account.code).all()

    if not all_accounts:
        st.info("لا توجد حسابات بعد.")
    else:
        # ---------- عرض الشجرة ----------
        main_accounts = [a for a in all_accounts if a.parent_id is None]

        for main_acc in main_accounts:
            _, _, main_bal = _balance_for(main_acc.id)
            with st.expander(
                f"📁 {main_acc.code} - {main_acc.name} ({main_acc.type.value})  —  رصيد: {main_bal:,.2f}",
                expanded=False,
            ):
                descendants = _flatten_tree(all_accounts, parent_id=main_acc.id, depth=1)
                if not descendants:
                    st.info("لا توجد حسابات فرعية.")
                else:
                    rows = []
                    for acc, depth in descendants:
                        indent = ("    " * (depth - 1)) + "└ " if depth > 1 else ""
                        d_, c_, b_ = _balance_for(acc.id)
                        rows.append({
                            "الكود": acc.code,
                            "الاسم": f"{indent}{acc.name}",
                            "مدين": d_,
                            "دائن": c_,
                            "الرصيد": b_,
                        })
                    df = pd.DataFrame(rows)
                    st.dataframe(
                        df, use_container_width=True, hide_index=True,
                        column_config={
                            "مدين": st.column_config.NumberColumn("مدين", format="%.2f"),
                            "دائن": st.column_config.NumberColumn("دائن", format="%.2f"),
                            "الرصيد": st.column_config.NumberColumn("الرصيد", format="%.2f"),
                        },
                    )

        st.markdown("---")

        # ---------- قسم التعديل والحذف ----------
        st.subheader("⚙️ تعديل / حذف حساب")

        account_ids = [a.id for a in all_accounts]
        selected_account_id = st.selectbox(
            "اختر حساباً:",
            options=account_ids,
            format_func=lambda x: next(
                (f"{a.code} - {a.name}" for a in all_accounts if a.id == x),
                str(x),
            ),
            key="sel_account_for_edit",
        )

        if selected_account_id:
            selected = next(
                (a for a in all_accounts if a.id == selected_account_id), None
            )
            usage = _account_usage(selected_account_id)
            used = _is_used(usage)

            # 📊 لوحة الاستخدام المفصّلة
            st.markdown("### 📊 معلومات الاستخدام التفصيلية")

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("🌳 حسابات فرعية", usage["sub_accounts"])
            with c2:
                st.metric("📋 أسطر القيود", usage["journal_lines"])
            with c3:
                st.metric("👥 عملاء/موردين", usage["parties"])
            with c4:
                st.metric("🏦 خزائن", usage["cash_boxes"])

            c5, c6, c7, c8 = st.columns(4)
            with c5:
                st.metric("📂 تصنيفات مصروفات", usage["expense_categories"])
            with c6:
                st.metric("💸 مصروفات", usage["expenses"])
            with c7:
                st.metric("🧾 فواتير (كعميل)", usage["invoices"])
            with c8:
                st.metric("💰 مدفوعات (كعميل)", usage["payments"])

            c9, c10, c11, c12 = st.columns(4)
            with c9:
                st.metric("📦 أصناف (مخزون)", usage["items_inventory"])
            with c10:
                st.metric("📦 أصناف (COGS)", usage["items_cogs"])
            with c11:
                st.metric("📦 أصناف (إيراد)", usage["items_revenue"])
            with c12:
                st.metric("🔄 تحويلات خزينة", usage["cash_transfers"])

            c13, c14, c15, c16 = st.columns(4)
            with c13:
                st.metric("🏛️ أصول ثابتة", usage["fixed_assets"])
            with c14:
                st.metric("💼 قروض", usage["loans"])
            with c15:
                st.metric("🏢 مراكز تكلفة", usage["cost_centers"])
            with c16:
                st.metric("📊 موازنات", usage["budgets"])

            # ═══════════════════════════════════════════════════════════
            # 📋 السجلات المرتبطة + أزرار الانتقال المباشر
            # ═══════════════════════════════════════════════════════════
            if used:
                st.markdown("### 📋 السجلات المرتبطة")

                party = db.query(Party).filter(Party.account_id == selected_account_id).first()
                cats = db.query(ExpenseCategory).filter(
                    ExpenseCategory.account_id == selected_account_id
                ).all()
                cashboxes = db.query(CashBox).filter(
                    CashBox.account_id == selected_account_id
                ).all()

                # ─── 1) الحسابات الفرعية ───
                if usage["sub_accounts"] > 0:
                    with st.expander(f"🌳 الحسابات الفرعية ({usage['sub_accounts']})", expanded=False):
                        subs = db.query(Account).filter(
                            Account.parent_id == selected_account_id
                        ).order_by(Account.code).all()
                        for s in subs:
                            col_a, col_b = st.columns([4, 1])
                            with col_a:
                                st.write(f"🔸 **{s.code}** — {s.name} ({s.type.value})")
                            with col_b:
                                if st.button("🔗 فتح", key=f"open_sub_{s.id}"):
                                    st.session_state["sel_account_for_edit"] = s.id
                                    st.rerun()

                # ─── 2) أسطر القيود ───
                if usage["journal_lines"] > 0:
                    with st.expander(f"📋 أسطر القيود ({usage['journal_lines']}) — آخر 10", expanded=False):
                        jl = db.query(models.JournalLine).filter(
                            models.JournalLine.account_id == selected_account_id
                        ).limit(10).all()
                        rows = []
                        for line in jl:
                            entry = db.query(models.JournalEntry).filter(
                                models.JournalEntry.id == line.entry_id
                            ).first()
                            if entry:
                                rows.append({
                                    "التاريخ": entry.date.strftime("%Y-%m-%d") if entry.date else "—",
                                    "الوصف": (entry.description or "")[:60],
                                    "مدين": float(line.debit or 0),
                                    "دائن": float(line.credit or 0),
                                })
                        st.dataframe(
                            pd.DataFrame(rows),
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "مدين": st.column_config.NumberColumn("مدين", format="%.2f"),
                                "دائن": st.column_config.NumberColumn("دائن", format="%.2f"),
                            },
                        )
                        if st.button("🔗 فتح حركات الخزينة", key=f"open_journal_{selected_account_id}"):
                            _goto_page("expenses", extra={"journal_filter_account": selected_account_id})

                # ─── 3) تصنيفات المصروفات ───
                if cats:
                    with st.expander(f"📂 تصنيفات المصروفات ({len(cats)})", expanded=True):
                        for c in cats:
                            col_a, col_b, col_c = st.columns([3, 1, 1])
                            with col_a:
                                st.write(f"📁 **{c.name}** — {(c.description or '')[:40]}")
                            with col_b:
                                exp_count = db.query(models.Expense).filter(
                                    models.Expense.category_id == c.id
                                ).count()
                                st.caption(f"💸 {exp_count} مصروف")
                            with col_c:
                                if st.button("🔗 فتح", key=f"open_cat_{c.id}"):
                                    _goto_page("expenses", extra={
                                        "open_expense_category_id": c.id,
                                        "open_expense_tab": "categories",
                                    })

                # ─── 4) المصروفات ───
                if usage["expenses"] > 0:
                    with st.expander(f"💸 المصروفات ({usage['expenses']}) — آخر 10", expanded=False):
                        cat_ids = [c.id for c in cats] if cats else []
                        if cat_ids:
                            exps = db.query(models.Expense).filter(
                                models.Expense.category_id.in_(cat_ids)
                            ).order_by(models.Expense.date.desc()).limit(10).all()
                            rows = []
                            for e in exps:
                                rows.append({
                                    "التاريخ": e.date.strftime("%Y-%m-%d") if e.date else "—",
                                    "المبلغ": float(e.amount or 0),
                                    "الوصف": (e.description or "")[:60],
                                })
                            st.dataframe(
                                pd.DataFrame(rows),
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "المبلغ": st.column_config.NumberColumn("المبلغ", format="%.2f"),
                                },
                            )
                        if st.button("🔗 فتح المصروفات", key=f"open_expenses_{selected_account_id}"):
                            _goto_page("expenses", extra={
                                "filter_expense_by_account": selected_account_id,
                            })

                # ─── 5) الخزائن ───
                if usage["cash_boxes"] > 0:
                    with st.expander(f"🏦 الخزائن ({usage['cash_boxes']})", expanded=False):
                        for b in cashboxes:
                            col_a, col_b = st.columns([4, 1])
                            with col_a:
                                st.write(f"🏦 **{b.code}** — {b.name} — رصيد: {float(b.balance or 0):,.2f}")
                            with col_b:
                                if st.button("🔗 فتح", key=f"open_box_{b.id}"):
                                    _goto_page("cash_boxes", record_id=b.id)

                # ─── 6) تحويلات الخزينة ───
                if usage["cash_transfers"] > 0 and cashboxes:
                    with st.expander(f"🔄 تحويلات الخزينة ({usage['cash_transfers']}) — آخر 10", expanded=False):
                        cashbox_ids = [b.id for b in cashboxes]
                        try:
                            transfers = db.query(models.CashTransfer).filter(
                                (models.CashTransfer.from_cash_box_id.in_(cashbox_ids)) |
                                (models.CashTransfer.to_cash_box_id.in_(cashbox_ids))
                            ).order_by(models.CashTransfer.date.desc()).limit(10).all()
                            rows = []
                            for t in transfers:
                                rows.append({
                                    "التاريخ": t.date.strftime("%Y-%m-%d") if t.date else "—",
                                    "المبلغ": float(t.amount or 0),
                                    "ملاحظات": (t.notes or "")[:60],
                                })
                            st.dataframe(
                                pd.DataFrame(rows),
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "المبلغ": st.column_config.NumberColumn("المبلغ", format="%.2f"),
                                },
                            )
                        except Exception:
                            st.info("لا يمكن عرض التفاصيل.")
                        if st.button("🔗 فتح حركات الخزينة", key=f"open_transfers_{selected_account_id}"):
                            _goto_page("expenses", extra={
                                "filter_by_account": selected_account_id,
                            })

                # ─── 7) العملاء والموردين ───
                if usage["parties"] > 0:
                    with st.expander(f"👥 العملاء والموردون ({usage['parties']})", expanded=False):
                        parties_list = db.query(Party).filter(
                            Party.account_id == selected_account_id
                        ).all()
                        for p in parties_list:
                            col_a, col_b = st.columns([4, 1])
                            with col_a:
                                st.write(f"👤 **{p.name}** — {p.type} — {p.phone or '—'}")
                            with col_b:
                                if st.button("🔗 فتح", key=f"open_party_{p.id}"):
                                    _goto_page("parties", record_id=p.id)

                # ─── 8) الفواتير ───
                if usage["invoices"] > 0 and party:
                    with st.expander(f"🧾 الفواتير ({usage['invoices']}) — آخر 10", expanded=False):
                        invs = db.query(models.Invoice).filter(
                            models.Invoice.party_id == party.id
                        ).order_by(models.Invoice.date.desc()).limit(10).all()
                        rows = []
                        for inv in invs:
                            rows.append({
                                "الرقم": inv.invoice_number or "—",
                                "التاريخ": inv.date.strftime("%Y-%m-%d") if inv.date else "—",
                                "النوع": inv.type or "—",
                                "الصافي": float(inv.net_amount or 0),
                                "الحالة": inv.status or "—",
                            })
                        st.dataframe(
                            pd.DataFrame(rows),
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "الصافي": st.column_config.NumberColumn("الصافي", format="%.2f"),
                            },
                        )
                        if st.button("🔗 فتح فهرس الفواتير", key=f"open_invoices_{selected_account_id}"):
                            _goto_page("invoices", extra={"filter_party_id": party.id})

                # ─── 9) المدفوعات ───
                if usage["payments"] > 0 and party:
                    with st.expander(f"💰 المدفوعات ({usage['payments']}) — آخر 10", expanded=False):
                        pays = db.query(models.Payment).filter(
                            models.Payment.party_id == party.id
                        ).order_by(models.Payment.date.desc()).limit(10).all()
                        rows = []
                        for p in pays:
                            rows.append({
                                "التاريخ": p.date.strftime("%Y-%m-%d") if p.date else "—",
                                "المبلغ": float(p.amount or 0),
                                "الطريقة": p.payment_method or "—",
                                "المرجع": p.reference_number or "—",
                            })
                        st.dataframe(
                            pd.DataFrame(rows),
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "المبلغ": st.column_config.NumberColumn("المبلغ", format="%.2f"),
                            },
                        )
                        if st.button("🔗 فتح المدفوعات", key=f"open_payments_{selected_account_id}"):
                            _goto_page("payments", extra={"filter_party_id": party.id})

                # ─── 10) الأصناف ───
                total_items = (usage["items_inventory"] + usage["items_cogs"] + usage["items_revenue"])
                if total_items > 0:
                    with st.expander(f"📦 الأصناف المرتبطة ({total_items})", expanded=False):
                        items_list = db.query(models.Item).filter(
                            (models.Item.inventory_account_id == selected_account_id) |
                            (models.Item.cogs_account_id == selected_account_id) |
                            (models.Item.revenue_account_id == selected_account_id)
                        ).limit(20).all()
                        for it in items_list:
                            roles = []
                            if it.inventory_account_id == selected_account_id:
                                roles.append("مخزون")
                            if it.cogs_account_id == selected_account_id:
                                roles.append("COGS")
                            if it.revenue_account_id == selected_account_id:
                                roles.append("إيراد")
                            col_a, col_b = st.columns([4, 1])
                            with col_a:
                                st.write(f"📦 **{it.barcode or '—'}** — {it.name} — {' + '.join(roles)}")
                            with col_b:
                                if st.button("🔗 فتح", key=f"open_item_{it.id}"):
                                    _goto_page("items", record_id=it.id)

                # ─── 11) الأصول الثابتة ───
                if usage["fixed_assets"] > 0:
                    with st.expander(f"🏛️ الأصول الثابتة ({usage['fixed_assets']})", expanded=False):
                        if st.button("🔗 فتح الأصول الثابتة", key=f"open_fa_{selected_account_id}"):
                            _goto_page("fixed_assets", extra={"filter_account_id": selected_account_id})

                # ─── 12) القروض ───
                if usage["loans"] > 0:
                    with st.expander(f"💼 القروض ({usage['loans']})", expanded=False):
                        if st.button("🔗 فتح القروض", key=f"open_loans_{selected_account_id}"):
                            _goto_page("loans", extra={"filter_account_id": selected_account_id})

                # ─── 13) مراكز التكلفة ───
                if usage["cost_centers"] > 0:
                    with st.expander(f"🏢 مراكز التكلفة ({usage['cost_centers']})", expanded=False):
                        if st.button("🔗 فتح مراكز التكلفة", key=f"open_cc_{selected_account_id}"):
                            _goto_page("cost_centers", extra={"filter_account_id": selected_account_id})

            st.markdown("---")

            # =========== التعديل ===========
            st.markdown("#### ✏️ تعديل الحساب")

            if usage["journal_lines"] > 0:
                st.warning("⚠️ لا يمكن التعديل — الحساب مستخدم في قيود يومية.")
            else:
                with st.form(f"edit_form_{selected_account_id}"):
                    new_code = st.text_input("الكود الجديد:", value=selected.code)
                    new_name = st.text_input("الاسم الجديد:", value=selected.name)
                    submitted = st.form_submit_button(
                        "💾 حفظ التعديلات", type="primary"
                    )

                if submitted:
                    try:
                        if not new_code.strip() or not new_name.strip():
                            st.error("❌ الكود والاسم مطلوبان.")
                        else:
                            dup = db.query(Account).filter(
                                Account.code == new_code.strip(),
                                Account.id != selected_account_id,
                            ).first()
                            if dup:
                                st.error(f"❌ الكود '{new_code}' مستخدم بالفعل في حساب آخر.")
                            else:
                                selected.code = new_code.strip()
                                selected.name = new_name.strip()
                                db.commit()
                                st.success("✅ تم تحديث الحساب بنجاح!")
                                st.rerun()
                    except Exception as e:
                        db.rollback()
                        st.error(f"❌ خطأ: {e}")

            st.markdown("---")

            # =========== الحذف ===========
            st.markdown("#### 🗑️ حذف الحساب")

            if used:
                st.error("⛔ **لا يمكن حذف هذا الحساب** — مرتبط بالسجلات أعلاه.")
                st.info(
                    "💡 **الحل:**\n"
                    "1. اضغط **🔗 فتح** بجانب أي سجل للانتقال إليه وتعديله أو حذفه\n"
                    "2. أو اجعل الحساب **غير مفعّل** بدل حذفه"
                )
            else:
                st.warning(
                    f"⚠️ سيتم حذف الحساب **{selected.code} - {selected.name}** نهائيًا."
                )
                confirm = st.checkbox(
                    "✅ أؤكد الحذف النهائي",
                    key=f"confirm_del_{selected_account_id}",
                )

                if st.button(
                    "🗑️ حذف الحساب نهائيًا",
                    type="secondary",
                    disabled=not confirm,
                    use_container_width=True,
                    key=f"del_btn_{selected_account_id}",
                ):
                    try:
                        deleted_name = selected.name
                        db.delete(selected)
                        db.commit()

                        st.success(f"✅ تم حذف الحساب '{deleted_name}' نهائيًا!")

                        queue_state_updates(
                            delete_keys=(
                                "sel_account_for_edit",
                                f"confirm_del_{selected_account_id}",
                            ),
                        )
                        st.rerun()
                    except Exception as e:
                        db.rollback()
                        st.error(f"❌ خطأ: {e}")

db.close()